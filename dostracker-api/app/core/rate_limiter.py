from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict

class RateLimiter:
    """Gestionnaire de rate limiting pour les endpoints sensibles"""
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window_minutes = window_minutes
        # Format: {ip_address: [(timestamp, username), ...]}
        self.attempts: Dict[str, List[tuple]] = defaultdict(list)
    
    def is_allowed(self, ip_address: str, username: str = None) -> tuple[bool, int]:
        """
        Vérifier si une tentative est autorisée
        Retourne (allowed: bool, remaining_attempts: int)
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=self.window_minutes)
        
        # Nettoyer les anciennes tentatives
        if ip_address in self.attempts:
            self.attempts[ip_address] = [
                (timestamp, user) for timestamp, user in self.attempts[ip_address]
                if timestamp > window_start
            ]
        
        # Compter les tentatives dans la fenêtre
        current_attempts = len(self.attempts[ip_address])
        
        if current_attempts >= self.max_attempts:
            return False, 0
        
        # Enregistrer la nouvelle tentative
        self.attempts[ip_address].append((now, username))
        remaining = self.max_attempts - current_attempts - 1
        
        return True, remaining
    
    def get_remaining_time(self, ip_address: str) -> int:
        """Obtenir le temps restant avant la réinitialisation (en secondes)"""
        if not self.attempts[ip_address]:
            return 0
        
        oldest_attempt = self.attempts[ip_address][0][0]
        window_end = oldest_attempt + timedelta(minutes=self.window_minutes)
        remaining = (window_end - datetime.utcnow()).total_seconds()
        
        return max(0, int(remaining))
    
    def reset(self, ip_address: str):
        """Réinitialiser les tentatives pour une IP"""
        if ip_address in self.attempts:
            del self.attempts[ip_address]

# Instance globale
login_rate_limiter = RateLimiter(max_attempts=5, window_minutes=15)
