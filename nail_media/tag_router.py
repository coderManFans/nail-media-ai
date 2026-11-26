import time
from .tag_schema import TagsV2

def route(image, primary, fallback, analyzer):
    attempts = []
    outputs = {}
    def call(model):
        start = time.monotonic()
        try:
            result = TagsV2.model_validate(analyzer(image,model)).result()
            outputs[model] = result
            attempts.append({"model":model,"seconds":round(time.monotonic()-start,3),"status":"ok"})
            return result
        except Exception as exc:
            attempts.append({"model":model,"seconds":round(time.monotonic()-start,3),"status":"failed","error":type(exc).__name__})
            return None
    first = call(primary)
    second = None
    if fallback and fallback != primary and (first is None or first["need_review"]):
        second = call(fallback)
    chosen = first or second
    differences = []
    if first and second:
        for key in ("content_type","nail_part","nail_shape","nail_length","colors","styles","finish","decorations"):
            a,b = first[key],second[key]
            if (set(a)!=set(b) if isinstance(a,list) else a!=b):
                differences.append(key)
    if chosen is None:
        return "failed",{"error":"AllModelsFailed","attempts":attempts}
    result = dict(chosen)
    if differences or first is None:
        result["need_review"] = True
        result["recommendation_eligible"] = False
        result["review_reasons"] = chosen["review_reasons"] + (["model_disagreement"] if differences else ["primary_failed"])
    result.update(model_attempts=attempts,model_outputs=outputs,model_differences=differences,selected_model=primary if first else fallback)
    return ("review" if result["need_review"] else "success"),result
