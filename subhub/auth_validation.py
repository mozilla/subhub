def basic_auth(api_token, required_scopes=None):
    if api_token:
        return {'token': api_token}

    # optional: raise exception for custom error response
    return None