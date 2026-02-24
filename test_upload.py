import requests

# 1. Start a session to get a session_id
chat_payload = {"message": "Hi"}
r1 = requests.post("http://localhost:8000/api/v3/chat", json=chat_payload)
print("Chat Response:", r1.status_code)
if r1.status_code == 200:
    session_id = r1.json().get("session_id")
    print("Got Session ID:", session_id)
    
    # 2. Upload a file
    with open("package.json", "rb") as f:
        files = {"file": ("tanish.pdf", f, "application/pdf")}
        data = {"session_id": session_id, "document_count": "1"}
        r2 = requests.post("http://localhost:8000/api/upload", files=files, data=data)
        print("Upload Status:", r2.status_code)
        try:
            print("Upload Response:", r2.json())
        except:
            print("Raw output:", r2.text)
