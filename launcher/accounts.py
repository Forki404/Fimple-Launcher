from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import paths, utils
from .config import get_config

ELY_AUTH_URL = "https://authserver.ely.by/auth/authenticate"
USER_AGENT = "FimpleLauncher/1.0 (ely.by client)"


@dataclass
class Account:
    id: str
    username: str
    type: str = "offline"
    uuid: str = ""
    accessToken: str = ""
    avatar: str = ""
    created: float = field(default_factory=time.time)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Account":
        return Account(
            id=d.get("id") or uuid.uuid4().hex[:12],
            username=d.get("username", "Player"),
            type=d.get("type", "offline"),
            uuid=d.get("uuid", ""),
            accessToken=d.get("accessToken", ""),
            avatar=d.get("avatar", ""),
            created=d.get("created", time.time()),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "username": self.username, "type": self.type,
            "uuid": self.uuid, "accessToken": self.accessToken,
            "avatar": self.avatar, "created": self.created,
        }

    @property
    def display(self) -> str:
        return f"{self.username} ({'Ely.by' if self.type == 'ely' else 'offline'})"


class AccountStore:
    def __init__(self) -> None:
        self._cfg = get_config()

    def all(self) -> List[Account]:
        return [Account.from_dict(a) for a in (self._cfg.get("accounts") or [])]

    def current(self) -> Optional[Account]:
        accounts = self.all()
        cur_id = self._cfg.get("current_account")
        for a in accounts:
            if a.id == cur_id:
                return a
        return accounts[0] if accounts else None

    def select(self, account_id: str) -> None:
        self._cfg.set("current_account", account_id)
        acc = next((a for a in self.all() if a.id == account_id), None)
        if acc:
            self._cfg.set("nickname", acc.username)
        self._cfg.save()

    def add(self, account: Account, make_current: bool = True) -> None:
        accounts = [a for a in (self._cfg.get("accounts") or []) if a.get("id") != account.id]
        accounts.append(account.to_dict())
        self._cfg.set("accounts", accounts)
        if make_current:
            self._cfg.set("current_account", account.id)
            self._cfg.set("nickname", account.username)
        if account.type == "ely":
            self._cfg.set("ely", {"accessToken": account.accessToken,
                                  "uuid": account.uuid,
                                  "username": account.username})
        self._cfg.save()

    def remove(self, account_id: str) -> None:
        accounts = [a for a in (self._cfg.get("accounts") or []) if a.get("id") != account_id]
        self._cfg.set("accounts", accounts)
        if self._cfg.get("current_account") == account_id:
            self._cfg.set("current_account", accounts[0].get("id") if accounts else None)
        self._cfg.save()

    def add_offline(self, username: str) -> Account:
        username = username.strip()
        if not username:
            raise ValueError("Пустой ник")
        for a in self.all():
            if a.username.lower() == username.lower() and a.type == "offline":
                self.select(a.id)
                return a
        acc = Account(id=uuid.uuid4().hex[:12], username=username, type="offline",
                      uuid=utils.offline_uuid(username))
        self.add(acc)
        return acc

    def login_ely(self, email: str, password: str) -> Account:
        import requests

        payload = {"username": email, "password": password, "requestUser": True}
        r = requests.post(ELY_AUTH_URL, json=payload, headers={"User-Agent": USER_AGENT},
                          timeout=15)
        if r.status_code != 200:
            try:
                err = r.json()
                msg = err.get("errorMessage") or err.get("error") or r.text
            except Exception:
                msg = r.text
            raise RuntimeError(str(msg))
        data = r.json()
        profile = data.get("selectedProfile") or {}
        if not profile:
            raise RuntimeError("У аккаунта нет выбранного профиля")
        acc = Account(
            id=uuid.uuid4().hex[:12],
            username=profile.get("name", ""),
            type="ely",
            uuid=profile.get("id", "").replace("-", ""),
            accessToken=data.get("accessToken", ""),
            avatar=profile.get("textures", {}).get("SKIN", {}).get("url", ""),
        )
        self.add(acc)
        return acc

    def avatar_path(self, account: Account) -> Optional[Path]:
        if account.type == "offline":
            return None
        cached = paths.cache_dir() / f"avatar_{account.uuid[:12]}.png"
        return cached if cached.exists() else None

    def fetch_avatar(self, account: Account) -> Optional[Path]:
        if not account.uuid:
            return None
        target = paths.cache_dir() / f"avatar_{account.uuid[:12]}.png"
        if target.exists():
            return target
        url = f"https://ely.by/avatar/{account.uuid[:32]}.png"
        try:
            import requests

            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            if r.status_code == 200 and r.content[:4] == b"\x89PNG":
                target.write_bytes(r.content)
                return target
        except Exception:
            pass
        return None


def store() -> AccountStore:
    return AccountStore()
