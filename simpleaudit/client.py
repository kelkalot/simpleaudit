"""
HTTP client for communicating with target AI systems.

Supports OpenAI-compatible chat completion APIs.
"""

from typing import List, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None


class TargetClient:
    """
    Client for interacting with OpenAI-compatible chat APIs.
    
    Args:
        base_url: Base URL of the API (should end with /v1/chat/completions or similar)
        model: Model name to send in requests
        timeout: Request timeout in seconds
        api_key: Optional API key for authenticated endpoints
    """
    
    def __init__(
        self,
        base_url: str,
        model: str = "default",
        timeout: float = 120.0,
        api_key: Optional[str] = None,
    ):
        if httpx is None:
            raise ImportError("httpx package required. Install with: pip install httpx")
        
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.conversation_history: List[Dict] = []
        
        # Build headers
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        self.client = httpx.Client(timeout=timeout, headers=headers)
    
    def reset(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def chat(self, message: str) -> str:
        """
        Send a message and get a response.
        
        Args:
            message: User message to send
        
        Returns:
            Assistant's response text
        """
        self.conversation_history.append({"role": "user", "content": message})
        
        # Determine endpoint
        if "/chat/completions" in self.base_url:
            url = self.base_url
        else:
            url = f"{self.base_url}/v1/chat/completions"
        
        response = self.client.post(
            url,
            json={
                "model": self.model,
                "messages": self.conversation_history,
            },
        )
        response.raise_for_status()
        
        assistant_message = response.json()["choices"][0]["message"]["content"]
        self.conversation_history.append({"role": "assistant", "content": assistant_message})
        
        return assistant_message
    
    def health_check(self) -> bool:
        """Check if the API is reachable."""
        try:
            # Try common health endpoints
            base = self.base_url.split("/v1")[0] if "/v1" in self.base_url else self.base_url
            
            for endpoint in ["/health", "/v1/models", "/"]:
                try:
                    response = self.client.get(f"{base}{endpoint}")
                    if response.status_code == 200:
                        return True
                except:
                    continue
            
            return False
        except:
            return False
