def choose_model(cfg: dict, tool: str, params: dict, fallback: str) -> str:
    rules = cfg.get("routing", {}).get(tool, [])
    for r in rules:
        cond = r.get("if")
        if cond == "default":
            return r["use"]
        if _eval(cond, params):
            return r["use"]
    return fallback

def _eval(expr: str, ctx: dict) -> bool:
    # Simple evaluator for conditions like "slides <= 3"
    parts = [p.strip() for p in expr.split("&&")]
    for p in parts:
        import re
        m = re.match(r"^(\w+)\s*(<=|>=|==|<|>)\s*(\w+)$", p)
        if not m:
            return False
        key, op, raw = m.groups()
        left = ctx.get(key)
        right = True if raw == "true" else False if raw == "false" else (float(raw) if raw.isdigit() else ctx.get(raw, raw))
        
        if op == "<=" and not (left <= right): return False
        if op == ">=" and not (left >= right): return False
        if op == "<" and not (left < right): return False
        if op == ">" and not (left > right): return False
        if op == "==" and not (left == right): return False
    return True