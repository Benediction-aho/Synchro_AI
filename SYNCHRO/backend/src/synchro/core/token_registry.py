import enum
import threading


class RegistryStatus(enum.Enum):
    OK = "ok"
    REUSED = "reused"
    UNKNOWN = "unknown"


class _FamilyState:
    __slots__ = ("active_jti", "used", "dead")

    def __init__(self, active_jti: str):
        self.active_jti = active_jti
        self.used: set[str] = set()
        self.dead = False


class TokenRegistry:
    """Tracks refresh-token lineage per session family.

    Replaying a rotated-out refresh token marks the whole family dead
    (stolen-token kill switch). In-memory for local dev; Redis backend later.
    """

    def __init__(self):
        self._families: dict[str, _FamilyState] = {}
        self._user_families: dict[int, set[str]] = {}
        self._lock = threading.Lock()

    def register(self, user_id: int, family_id: str, jti: str) -> None:
        with self._lock:
            self._families[family_id] = _FamilyState(jti)
            self._user_families.setdefault(user_id, set()).add(family_id)

    def exchange(self, family_id: str, presented_jti: str, new_jti: str) -> RegistryStatus:
        with self._lock:
            family = self._families.get(family_id)
            if family is None:
                return RegistryStatus.UNKNOWN
            if family.dead or family.active_jti != presented_jti:
                family.dead = True
                return RegistryStatus.REUSED
            family.used.add(presented_jti)
            family.active_jti = new_jti
            return RegistryStatus.OK

    def kill_family(self, family_id: str) -> None:
        with self._lock:
            family = self._families.get(family_id)
            if family is not None:
                family.dead = True

    def kill_all_for_user(self, user_id: int) -> int:
        with self._lock:
            families = self._user_families.pop(user_id, set())
            killed = 0
            for fid in families:
                family = self._families.get(fid)
                if family is not None and not family.dead:
                    family.dead = True
                    killed += 1
            return killed

    def is_dead(self, family_id: str) -> bool:
        with self._lock:
            family = self._families.get(family_id)
            return family is None or family.dead
