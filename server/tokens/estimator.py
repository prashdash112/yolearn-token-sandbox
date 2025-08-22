import json
import math
import uuid
import pathlib
from .routing import choose_model

CFG = json.loads((pathlib.Path(__file__).resolve().parents[2] / "pricing/pricing_baselines.json").read_text())

class EstimateResult(dict):
    pass

def estimate(tool: str, params: dict) -> EstimateResult:
    bd = []
    baseline = 0.0
    model_used = None
    
    def add(component, unit, qty, unit_usd):
        nonlocal baseline
        cost = qty * unit_usd
        baseline += cost
        bd.append({
            "component": component,
            "unit": unit,
            "quantity": qty,
            "baseline_usd": round(cost, 6)
        })
    
    if tool == "chat":
        model_used = choose_model(CFG, "chat", params, CFG["tools"]["chat"]["default_model"])
        out1k = params.get("expected_out_1k", CFG["tools"]["chat"].get("est_out_1k", 0.8))
        add(f"llm_{model_used}_out", "1k_tokens", out1k, CFG["models"][model_used]["out_1k"])
    
    elif tool == "flashcards":
        n = int(params.get("cards", 20))
        model_used = CFG["tools"]["flashcards"]["llm"]
        out_units = n * CFG["tools"]["flashcards"]["per_card_out_1k_est"]
        add(f"llm_{model_used}_out", "1k_tokens", out_units, CFG["models"][model_used]["out_1k"])
    
    elif tool == "ppt":
        s = int(params.get("slides", 5))
        include_images = params.get("include_images", CFG["tools"]["ppt"]["with_images"])
        image_res = str(params.get("image_res", CFG["tools"]["ppt"]["image_res"]))
        model_used = choose_model(CFG, "ppt", {"slides": s, "images": bool(include_images)}, CFG["tools"]["ppt"]["llm"])
        
        add(f"llm_{model_used}_out", "1k_tokens", s * CFG["tools"]["ppt"]["per_slide_out_1k_est"], CFG["models"][model_used]["out_1k"])
        
        if include_images:
            price = CFG["image"]["gen"][image_res]
            add(f"image_gen_{image_res}", "image", s * CFG["tools"]["ppt"].get("images_per_slide", 1), price)
    
    elif tool == "short_video":
        sec = int(params.get("duration_sec", 120))
        minutes = sec / 60
        script_model = CFG["tools"]["short_video"]["script_llm"]
        
        add(f"llm_{script_model}_out", "1k_tokens", params.get("script_out_1k_est", CFG["tools"]["short_video"]["script_out_1k_est"]), CFG["models"][script_model]["out_1k"])
        add("tts_11labs", "min", minutes, CFG["audio"]["tts_11labs"]["per_min"])
        
        quality = params.get("quality", CFG["tools"]["short_video"]["quality"])
        band = "sd_per_min" if quality == "sd" else "hd_per_min"
        add(f"video_did_{band}", "min", minutes, CFG["video"]["did"][band])
    
    elif tool == "live_audio_chat":
        minutes = float(params.get("minutes", 10))
        out1k_per_min = float(params.get("out_1k_per_min", CFG["tools"]["live_audio_chat"]["out_1k_per_min"]))
        llm = CFG["tools"]["live_audio_chat"]["llm"]
        
        add("stt", "min", minutes, CFG["audio"]["stt"]["per_min"])
        add("tts_11labs", "min", minutes, CFG["audio"]["tts_11labs"]["per_min"])
        add(f"llm_{llm}_out", "1k_tokens", out1k_per_min * minutes, CFG["models"][llm]["out_1k"])
    
    retail = baseline * (1 + CFG["margin"])
    tokens = max(CFG["min_charge_tokens"], math.ceil(retail / CFG["token_value_usd"]))
    hold = math.ceil(tokens * (1 + CFG["safety_buffer"]))
    
    return EstimateResult({
        "estimate_tokens": tokens,
        "hold_tokens": hold,
        "baseline_usd": round(baseline, 6),
        "retail_usd": round(retail, 6),
        "breakdown": bd,
        "model_used": model_used
    })

def new_id():
    return uuid.uuid4().hex[:32]