SIGNUP = {"name": "Ada", "email": "Ada@Example.com", "password": "password123", "account_type": "storyteller"}


def signup(client, **overrides):
    return client.post("/api/auth/signup", json={**SIGNUP, **overrides})


def auth(token):
    return {"Authorization": f"Bearer {token}"}
