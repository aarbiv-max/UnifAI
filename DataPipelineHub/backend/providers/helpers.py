def get_scope_filters(source_type, scope, user):
    if scope == "private":
        # Only documents uploaded by the user
        return {"source_type": source_type, "upload_by": user, "deleted": {"$ne": True}}
    elif scope == "public":
        # Documents uploaded by the user OR public documents (from any user)
        return {
            "source_type": source_type,
            "deleted": {"$ne": True},
            "$or": [{"upload_by": user}, {"scope": "public"}]}
    else:
        # Default to private scope
        return {"source_type": source_type, "upload_by": user, "deleted": {"$ne": True}}
