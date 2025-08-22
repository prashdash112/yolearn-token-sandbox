from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Wallet(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    balance_tokens = models.IntegerField(default=0)
    hold_tokens = models.IntegerField(default=0)

class LedgerEntry(models.Model):
    id = models.CharField(primary_key=True, max_length=32)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="ledger")
    delta_tokens = models.IntegerField()  # +credit, -debit
    reason = models.CharField(max_length=64)
    task_code = models.CharField(max_length=64, null=True, blank=True)
    idempotency_key = models.CharField(max_length=128, unique=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Quote(models.Model):
    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED" 
    SETTLED = "SETTLED"
    
    id = models.CharField(primary_key=True, max_length=32)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    tool = models.CharField(max_length=32)
    params = models.JSONField(default=dict)
    estimate_tokens = models.IntegerField()
    hold_tokens = models.IntegerField()
    status = models.CharField(max_length=16, default=PENDING)
    model_used = models.CharField(max_length=64, null=True, blank=True)
    baseline_usd = models.FloatField(default=0)
    retail_usd = models.FloatField(default=0)
    breakdown = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

class Hold(models.Model):
    ACTIVE = "ACTIVE"
    CAPTURED = "CAPTURED"
    RELEASED = "RELEASED"
    
    id = models.CharField(primary_key=True, max_length=32)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE)
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="holds")
    tokens = models.IntegerField()
    status = models.CharField(max_length=16, default=ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

class ActualUsage(models.Model):
    quote = models.OneToOneField(Quote, on_delete=models.CASCADE, primary_key=True, related_name="usage")
    llm_in_1k = models.FloatField(default=0)
    llm_out_1k = models.FloatField(default=0)
    stt_min = models.FloatField(default=0)
    tts_min = models.FloatField(default=0)
    video_min = models.FloatField(default=0)
    images_1024 = models.IntegerField(default=0)
    images_2048 = models.IntegerField(default=0)
    gpu_seconds = models.IntegerField(default=0)
    meta = models.JSONField(default=dict, blank=True)