from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.contrib.auth.models import User

from .models import Wallet, LedgerEntry, Quote, Hold, ActualUsage
from .serializers import QuoteReq, UsageReq
from .estimator import estimate, new_id

def demo_user():
    u, _ = User.objects.get_or_create(username="demo")
    w, _ = Wallet.objects.get_or_create(id="wallet_demo", user=u)
    if w.balance_tokens < 500:
        credit(w, 500, reason="demo_seed", idem=f"seed:{w.id}:500")
    return u

@api_view(["GET"])
def wallet_view(request):
    u = demo_user()
    w = u.wallet
    entries = list(w.ledger.order_by("-created_at").values("delta_tokens", "reason", "created_at")[:10])
    return Response({
        "balance": w.balance_tokens,
        "on_hold": w.hold_tokens,
        "recent": entries
    })

@api_view(["POST"])
def create_quote(request):
    u = demo_user()
    w = u.wallet
    ser = QuoteReq(data=request.data)
    ser.is_valid(raise_exception=True)
    
    tool = ser.validated_data["tool"]
    params = ser.validated_data.get("params", {})
    
    est = estimate(tool, params)
    q = Quote(
        id=new_id(),
        user=u,
        wallet=w,
        tool=tool,
        params=params,
        estimate_tokens=est["estimate_tokens"],
        hold_tokens=est["hold_tokens"],
        baseline_usd=est["baseline_usd"],
        retail_usd=est["retail_usd"],
        breakdown=est["breakdown"],
        model_used=est.get("model_used")
    )
    q.save()
    
    return Response({"quote_id": q.id, **est})

@api_view(["POST"])
@transaction.atomic
def authorize(request, quote_id: str):
    u = demo_user()
    w = u.wallet
    q = Quote.objects.get(id=quote_id, user=u)
    
    if q.status != Quote.PENDING:
        return Response({"error": "Invalid quote state"}, status=400)
    
    hold_tokens(w, q.hold_tokens, idem=f"quote_hold:{q.id}")
    q.status = Quote.AUTHORIZED
    q.save()
    
    return Response({"status": q.status})

@api_view(["POST"])
def push_usage(request):
    ser = UsageReq(data=request.data)
    ser.is_valid(raise_exception=True)
    data = ser.validated_data
    
    q = Quote.objects.get(id=data["quote_id"])
    au = ActualUsage(
        quote=q,
        llm_in_1k=data["llm_in_1k"],
        llm_out_1k=data["llm_out_1k"],
        stt_min=data["stt_min"],
        tts_min=data["tts_min"],
        video_min=data["video_min"],
        images_1024=data["images_1024"],
        images_2048=data["images_2048"],
        gpu_seconds=data["gpu_seconds"],
        meta=data.get("meta", {})
    )
    au.save()
    
    return Response({"ok": True})

@api_view(["POST"])
@transaction.atomic
def settle(request, quote_id: str):
    u = demo_user()
    w = u.wallet
    q = Quote.objects.get(id=quote_id)
    
    if not hasattr(q, "usage"):
        return Response({"error": "Usage missing"}, status=400)
    
    from .estimator import CFG
    au = q.usage
    baseline = 0.0
    
    if q.model_used:
        baseline += (au.llm_out_1k or 0) * CFG["models"][q.model_used]["out_1k"]
    baseline += (au.tts_min or 0) * CFG["audio"]["tts_11labs"]["per_min"]
    baseline += (au.stt_min or 0) * CFG["audio"]["stt"]["per_min"]
    baseline += (au.video_min or 0) * CFG["video"]["did"]["hd_per_min"]
    baseline += (au.images_1024 or 0) * CFG["image"]["gen"]["1024"]
    baseline += (au.images_2048 or 0) * CFG["image"]["gen"]["2048"]
    
    retail = baseline * (1 + CFG["margin"])
    actual_tokens = max(CFG["min_charge_tokens"], int(-(-retail // CFG["token_value_usd"])))
    
    capture_from_hold(w, requested=actual_tokens, hold_idem=f"quote_hold:{q.id}")
    q.status = Quote.SETTLED
    q.save()
    
    return Response({
        "charged_tokens": actual_tokens,
        "held": q.hold_tokens,
        "refund": q.hold_tokens - actual_tokens
    })

# Wallet helper functions
def credit(wallet: Wallet, tokens: int, reason: str, idem: str):
    if LedgerEntry.objects.filter(idempotency_key=idem).exists():
        return
    wallet.balance_tokens += tokens
    wallet.save(update_fields=["balance_tokens"])
    LedgerEntry.objects.create(
        id=new_id(),
        wallet=wallet,
        delta_tokens=tokens,
        reason=reason,
        idempotency_key=idem
    )

def hold_tokens(wallet: Wallet, tokens: int, idem: str):
    if LedgerEntry.objects.filter(idempotency_key=idem).exists():
        return
    if wallet.balance_tokens < tokens:
        raise ValueError("Insufficient tokens for hold")
    
    wallet.balance_tokens -= tokens
    wallet.hold_tokens += tokens
    wallet.save(update_fields=["balance_tokens", "hold_tokens"])
    LedgerEntry.objects.create(
        id=new_id(),
        wallet=wallet,
        delta_tokens=0,
        reason="hold",
        idempotency_key=idem,
        meta={"held": tokens}
    )

def capture_from_hold(wallet: Wallet, requested: int, hold_idem: str):
    le = LedgerEntry.objects.filter(idempotency_key=hold_idem).first()
    held = le.meta.get("held", 0) if le else 0
    charge = min(held, requested)
    refund = max(0, held - charge)
    
    wallet.hold_tokens -= held
    wallet.balance_tokens += refund
    wallet.save(update_fields=["balance_tokens", "hold_tokens"])
    
    LedgerEntry.objects.create(
        id=new_id(),
        wallet=wallet,
        delta_tokens=-charge,
        reason="capture",
        idempotency_key=f"cap:{hold_idem}"
    )
    
    if refund:
        LedgerEntry.objects.create(
            id=new_id(),
            wallet=wallet,
            delta_tokens=refund,
            reason="refund",
            idempotency_key=f"ref:{hold_idem}"
        )