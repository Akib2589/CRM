# app/validators/duplicate_detector.py
from typing import List, Dict, Any, Tuple
from rapidfuzz import fuzz
from app.utils.normalization import normalize_company_name

def compute_company_similarity(name1: str, name2: str) -> float:
    norm1 = normalize_company_name(name1)
    norm2 = normalize_company_name(name2)
    
    if norm1 == norm2 and norm1:
        return 100.0
        
    score_token_sort = fuzz.token_sort_ratio(norm1, norm2)
    score_ratio = fuzz.ratio(norm1, norm2)
    return max(score_token_sort, score_ratio)

def detect_duplicates(
    company_name: str,
    contact_email: str | None,
    existing_records: List[Dict[str, Any]],
    threshold: float = 85.0
) -> List[Dict[str, Any]]:
    """
    existing_records format:
    [{'id': int, 'name': str, 'normalized_name': str, 'contact_email': str | None, 'lead_id': int | None}]
    """
    candidates = []
    norm_target = normalize_company_name(company_name)
    
    for rec in existing_records:
        rec_name = rec.get("name", "")
        rec_norm = rec.get("normalized_name") or normalize_company_name(rec_name)
        rec_email = rec.get("contact_email")
        
        sim_score = compute_company_similarity(company_name, rec_name)
        is_same_email = bool(contact_email and rec_email and contact_email.strip().lower() == rec_email.strip().lower())
        
        # Exact match, high similarity, or same contact email with partial name match
        if sim_score >= threshold or (is_same_email and sim_score >= 65.0):
            candidates.append({
                "target_company": company_name,
                "matched_company": rec_name,
                "matched_id": rec.get("id"),
                "matched_lead_id": rec.get("lead_id"),
                "similarity_score": round(sim_score, 1),
                "is_same_email": is_same_email,
                "reason": f"Matches existing company '{rec_name}' (similarity {round(sim_score, 1)}%)" + 
                          (" with identical contact email" if is_same_email else "")
            })
            
    return candidates
