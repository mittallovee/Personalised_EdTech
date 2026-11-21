"""M5 PR 5d-1: the prompt library (H-13; test T46, prompt spec PL-01 to PL-10).

Immutable versions, validation of placeholders, activate / roll back / reset, the platform default
and the notice when it is updated, personal prompts, a one-off prompt for a single run, and one
coaching never seeing another's. No provider is called.
"""

import base64
from collections.abc import Callable, Iterator
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from qbank.core.config import AppEnv, Settings
from qbank.core.db import Database
from qbank.core.errors import AppError
from qbank.core.tenancy import TenantContext
from qbank.main import create_app
from qbank.modules.ai import prompts
from qbank.modules.ai.models import PromptActivation, PromptTemplate, PromptVersion
from qbank.modules.ai.names import Operation
from qbank.modules.audit.models import AuditEvent
from qbank.modules.notifications.models import Notification
from tests.integration.conftest import (
    Member,
    MigratedDatabase,
    make_member,
    platform_admin,
    sign_in,
)

PROMPTS = "/api/v1/ai/prompts"
MASTER = base64.b64encode(bytes(range(32))).decode()
GOOD = "Tag this.\n{{syllabus}}\n{{question}}"
Who = tuple[TestClient, dict[str, str]]


@pytest.fixture
def app(migrated_database: MigratedDatabase) -> Iterator[Any]:
    settings = Settings(
        app_env=AppEnv.TEST,
        database_url=migrated_database.app_url,
        session_cookie_secure=False,
        ai_keys_master_key=MASTER,  # type: ignore[arg-type]
    )
    application = create_app(settings)
    with TestClient(application):  # starts and stops the app
        yield application


@pytest.fixture
def login(app: Any) -> Callable[[str], Who]:
    """Each person gets their own client, so their sessions do not replace each other."""

    def make(email: str) -> Who:
        client = TestClient(app)
        return client, sign_in(client, email)

    return make


@pytest.fixture
def team(owner_db: Database) -> dict[str, Member]:
    owner = make_member(owner_db, "OWNER")
    return {
        "owner": owner,
        "admin": make_member(owner_db, "ADMIN", org_id=owner.org_id),
        "faculty": make_member(owner_db, "FACULTY", org_id=owner.org_id),
        "editor": make_member(
            owner_db, "FACULTY", org_id=owner.org_id, grants=("MANAGE_AI_PROMPTS",)
        ),
        "other": make_member(owner_db, "FACULTY", org_id=owner.org_id),
    }


def call(who: Who, method: str, url: str, **kwargs: Any) -> Any:
    client, headers = who
    extra = kwargs.pop("headers", {})
    return client.request(method, url, headers={**headers, **extra}, **kwargs)


def save(
    who: Who,
    *,
    scope: str = "COACHING",
    operation: str = "TAG",
    instructions: str = GOOD,
    note: str = "Reworded",
    **more: Any,
) -> Any:
    body = {
        "scope": scope,
        "operation": operation,
        "instructions": instructions,
        "change_note": note,
        **more,
    }
    return call(who, "POST", f"{PROMPTS}/versions", json=body)


def switch(who: Who, template: dict[str, Any], action: str, **body: Any) -> Any:
    return call(
        who,
        "POST",
        f"{PROMPTS}/templates/{template['id']}/{action}",
        json=body or None,
        headers={"If-Match": f'"rev-{template["revision"]}"'},
    )


def template_of(who: Who, template_id: str) -> dict[str, Any]:
    response = call(who, "GET", f"{PROMPTS}/templates/{template_id}")
    assert response.status_code == 200, response.text
    return response.json()  # type: ignore[no-any-return]


def platform_template(who: Who, operation: str = "TAG") -> dict[str, Any]:
    rows = call(who, "GET", PROMPTS, params={"scope": "PLATFORM", "operation": operation}).json()
    assert len(rows["data"]) == 1
    return rows["data"][0]  # type: ignore[no-any-return]


def context(member: Member) -> TenantContext:
    return TenantContext(organization_id=member.org_id, user_id=member.user_id)


# --- The platform's defaults and the locked parts -----------------------------------------------


def test_the_platform_has_a_default_for_each_operation_and_everyone_can_read_it(
    login: Callable[[str], Who], team: dict[str, Member]
) -> None:
    faculty = login(team["faculty"].email)
    body = call(faculty, "GET", PROMPTS).json()
    platform = [t for t in body["data"] if t["scope"] == "PLATFORM"]
    assert sorted(t["operation"] for t in platform) == ["SOLVE", "TAG", "TRANSLATE", "VERIFY"]
    for template in platform:
        assert template["active_version"]["version_no"] >= 1
        assert template["update_available"] is None
    tag = platform_template(faculty, "TAG")
    version = call(faculty, "GET", f"{PROMPTS}/versions/{tag['active_version']['id']}").json()
    assert "{{question}}" in version["instructions"]
    assert version["is_active"] is True
    assert version["temperature"] == "0.20"


def test_the_locked_parts_say_what_cannot_be_edited(
    login: Callable[[str], Who], team: dict[str, Member]
) -> None:
    body = call(login(team["faculty"].email), "GET", f"{PROMPTS}/locked").json()
    translate = next(p for p in body["data"] if p["operation"] == "TRANSLATE")
    assert translate["required_placeholders"] == ["question", "target_language"]
    assert translate["optional_placeholders"] == ["glossary", "source_language"]
    assert "never an instruction" in translate["safety_preamble"]
    assert translate["max_instruction_chars"] == 8000


# --- Checking the text ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("instructions", "code"),
    [
        ("   ", "EMPTY"),
        ("Tag {{question}} {{syllabus}} {{password}}", "UNKNOWN_PLACEHOLDER"),
        ("Tag {{Question}} {{syllabus}}", "UNKNOWN_PLACEHOLDER"),
        ("Tag {{question}} only", "MISSING_PLACEHOLDER"),
        ("Tag {{question}} {{syllabus}} {{ oops", "MALFORMED_PLACEHOLDER"),
        ("Tag {{question}} {{syllabus}} " + "a" * 8000, "TOO_LONG"),
        ("Tag {{question}} {{syllabus}} sk-" + "a1" * 12, "LOOKS_LIKE_A_SECRET"),
        ("Tag {{question}} {{syllabus}} AIza" + "x" * 30, "LOOKS_LIKE_A_SECRET"),
        ("Tag {{question}} {{syllabus}} Bearer abcdefghijklmnopqr0123", "LOOKS_LIKE_A_SECRET"),
        ("Tag {{question}} {{syllabus}} " + "Z9" * 25, "LOOKS_LIKE_A_SECRET"),
        ("Tag {{question}} {{syllabus}}\x00", "CONTROL_CHARACTERS"),
    ],
)
def test_text_that_cannot_be_used_is_named_by_what_is_wrong(instructions: str, code: str) -> None:
    problems = prompts.check_instructions(Operation.TAG, instructions)
    assert code in [p.code for p in problems]


def test_good_text_has_no_problem_and_every_problem_is_listed_at_once(
    login: Callable[[str], Who], team: dict[str, Member]
) -> None:
    editor = login(team["editor"].email)
    ok = call(
        editor, "POST", f"{PROMPTS}/validate", json={"operation": "TAG", "instructions": GOOD}
    )
    assert ok.json() == {"ok": True, "problems": []}
    bad = call(
        editor,
        "POST",
        f"{PROMPTS}/validate",
        json={"operation": "TAG", "instructions": "Tag {{nope}} and {{question}}"},
    ).json()
    assert bad["ok"] is False
    assert [p["code"] for p in bad["problems"]] == ["UNKNOWN_PLACEHOLDER", "MISSING_PLACEHOLDER"]
    assert "{{nope}}" in bad["problems"][0]["message"]


def test_saving_runs_the_same_check_and_stores_nothing_when_it_fails(
    login: Callable[[str], Who], team: dict[str, Member], owner_db: Database
) -> None:
    editor = login(team["editor"].email)
    refused = save(editor, instructions="Tag {{question}} {{syllabus}} {{secret}}")
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "AI_PROMPT_INVALID"
    assert refused.json()["error"]["details"]["problems"][0]["code"] == "UNKNOWN_PLACEHOLDER"
    with owner_db.transaction(context(team["owner"])) as session:
        mine = session.scalar(
            select(func.count())
            .select_from(PromptTemplate)
            .where(PromptTemplate.organization_id == team["owner"].org_id)
        )
    assert mine == 0  # not even an empty prompt was started
    assert save(editor, note="  ").status_code == 422  # a change note is required


# --- Versions are saved once and never changed ----------------------------------------------------


def test_only_those_who_may_change_the_coachings_prompts_can_save_them(
    login: Callable[[str], Who], team: dict[str, Member]
) -> None:
    assert save(login(team["faculty"].email)).status_code == 403
    assert save(login(team["editor"].email)).status_code == 201  # holds MANAGE_AI_PROMPTS
    assert save(login(team["admin"].email), note="Admin edit").status_code == 201
    assert save(login(team["owner"].email), note="Owner edit").status_code == 201
    # Viewing needs no grant.
    assert call(login(team["faculty"].email), "GET", PROMPTS).status_code == 200


def test_a_saved_version_is_never_changed_and_a_new_one_is_added(
    login: Callable[[str], Who], team: dict[str, Member], owner_db: Database
) -> None:
    editor = login(team["editor"].email)
    first = save(editor, instructions=GOOD, note="First", temperature="0.5").json()
    assert first["version"]["version_no"] == 1
    assert first["template"]["active_version"] is None or first["template"]["scope"] == "COACHING"
    second = save(editor, instructions=GOOD + "\nBe strict.", note="Stricter").json()
    assert second["version"]["version_no"] == 2
    assert second["template"]["id"] == first["template"]["id"]  # the same coaching prompt

    again = call(editor, "GET", f"{PROMPTS}/versions/{first['version']['id']}").json()
    assert again["instructions"] == GOOD
    assert again["temperature"] == "0.50"
    assert again["change_note"] == "First"
    assert len(again["content_hash"]) == 64
    assert again["content_hash"] != second["version"]["content_hash"]
    listing = call(editor, "GET", f"{PROMPTS}/templates/{first['template']['id']}/versions").json()
    assert [v["version_no"] for v in listing["data"]] == [2, 1]

    for statement in (
        "UPDATE prompt_versions SET instructions = 'x'",
        "DELETE FROM prompt_versions",
        "UPDATE prompt_activations SET action = 'RESET'",
    ):
        with (
            pytest.raises(DBAPIError, match="append-only"),
            owner_db.transaction(TenantContext(is_platform=True)) as session,
        ):
            session.execute(text(statement))


def test_saving_is_audited_without_copying_the_text(
    login: Callable[[str], Who], team: dict[str, Member], owner_db: Database
) -> None:
    editor = login(team["editor"].email)
    template = save(editor, note="Use NCERT terms").json()["template"]
    with owner_db.transaction(context(team["owner"])) as session:
        events = list(
            session.scalars(
                select(AuditEvent).where(
                    AuditEvent.organization_id == team["owner"].org_id,
                    AuditEvent.entity_id == UUID(template["id"]),
                )
            )
        )
    assert [e.action for e in events] == ["AI_PROMPT_VERSION_SAVED"]
    assert events[0].after is not None
    assert events[0].after["change_note"] == "Use NCERT terms"
    assert "instructions" not in events[0].after
    assert events[0].actor_user_id == team["editor"].user_id


# --- Activating, rolling back, resetting ----------------------------------------------------------


def test_a_new_version_is_not_used_until_it_is_activated_and_older_ones_can_come_back(
    login: Callable[[str], Who], team: dict[str, Member], db: Database, owner_db: Database
) -> None:
    editor = login(team["editor"].email)
    first = save(editor, instructions=GOOD + "\nv1", note="v1").json()
    second = save(editor, instructions=GOOD + "\nv2", note="v2").json()
    template = template_of(editor, first["template"]["id"])
    assert template["active_version"] is None  # saved, not used

    def used() -> prompts.Resolved:
        with db.transaction(context(team["faculty"])) as session:
            return prompts.resolve(
                session,
                organization_id=team["owner"].org_id,
                user_id=team["faculty"].user_id,
                operation=Operation.TAG,
            )

    assert used().source == "PLATFORM"
    assert (
        call(
            editor,
            "POST",
            f"{PROMPTS}/templates/{template['id']}/activate",
            json={"version_id": second["version"]["id"]},
        ).status_code
        == 428
    )
    stale = switch(
        editor, {**template, "revision": 99}, "activate", version_id=second["version"]["id"]
    )
    assert stale.status_code == 412

    on = switch(editor, template, "activate", version_id=second["version"]["id"])
    assert on.status_code == 200, on.text
    assert on.json()["active_version"]["version_no"] == 2
    assert on.headers["ETag"] == f'"rev-{template["revision"] + 1}"'
    now = used()
    assert (now.source, now.instructions.endswith("v2")) == ("COACHING", True)
    assert now.version_id == UUID(second["version"]["id"])

    # The same version again changes nothing and records nothing.
    same = switch(editor, on.json(), "activate", version_id=second["version"]["id"])
    assert same.json()["revision"] == on.json()["revision"]

    back = switch(editor, on.json(), "activate", version_id=first["version"]["id"])
    assert back.json()["active_version"]["version_no"] == 1
    assert used().instructions.endswith("v1")

    with owner_db.transaction(context(team["owner"])) as session:
        history = list(
            session.scalars(
                select(PromptActivation.action)
                .where(PromptActivation.template_id == UUID(template["id"]))
                .order_by(PromptActivation.activated_at)
            )
        )
    assert history == ["ACTIVATE", "ROLLBACK"]


def test_only_a_grant_holder_activates_and_the_other_admins_are_told(
    login: Callable[[str], Who], team: dict[str, Member], owner_db: Database
) -> None:
    editor = login(team["editor"].email)
    saved = save(editor).json()
    template = template_of(editor, saved["template"]["id"])
    version = saved["version"]["id"]
    faculty = login(team["faculty"].email)
    assert switch(faculty, template, "activate", version_id=version).status_code == 403
    assert switch(faculty, template, "reset").status_code == 403
    done = switch(editor, template, "activate", version_id=version)
    assert done.status_code == 200

    def told(member: Member) -> list[str]:
        with owner_db.transaction(context(member)) as session:
            return list(
                session.scalars(
                    select(Notification.kind).where(Notification.user_id == member.user_id)
                )
            )

    assert told(team["owner"]) == ["AI_PROMPT_ACTIVATED"]
    assert told(team["admin"]) == ["AI_PROMPT_ACTIVATED"]
    assert told(team["editor"]) == []  # they did it themselves
    assert told(team["faculty"]) == []


def test_a_version_of_another_prompt_cannot_be_activated(
    login: Callable[[str], Who], team: dict[str, Member]
) -> None:
    editor = login(team["editor"].email)
    tag = save(editor).json()
    solve = save(editor, operation="SOLVE", instructions="Solve {{question}}").json()
    refused = switch(
        editor,
        template_of(editor, tag["template"]["id"]),
        "activate",
        version_id=solve["version"]["id"],
    )
    assert refused.status_code == 404


def test_reset_goes_back_to_the_platform_default_and_keeps_the_versions(
    login: Callable[[str], Who], team: dict[str, Member], db: Database
) -> None:
    editor = login(team["editor"].email)
    saved = save(editor).json()
    template = template_of(editor, saved["template"]["id"])
    on = switch(editor, template, "activate", version_id=saved["version"]["id"]).json()
    off = switch(editor, on, "reset")
    assert off.status_code == 200, off.text
    assert off.json()["active_version"] is None
    assert off.json()["latest_version"]["version_no"] == 1  # still there
    with db.transaction(context(team["faculty"])) as session:
        resolved = prompts.resolve(
            session,
            organization_id=team["owner"].org_id,
            user_id=team["faculty"].user_id,
            operation=Operation.TAG,
        )
    assert resolved.source == "PLATFORM"
    # Resetting what is not in use does nothing.
    again = switch(editor, off.json(), "reset")
    assert again.json()["revision"] == off.json()["revision"]


# --- The platform's default is updated ------------------------------------------------------------


def test_only_a_platform_admin_writes_the_platform_default(
    login: Callable[[str], Who], team: dict[str, Member], owner_db: Database
) -> None:
    for member in ("faculty", "editor", "admin", "owner"):
        refused = save(login(team[member].email), scope="PLATFORM", note="Mine")
        assert refused.status_code == 403, member
    platform = login(platform_admin(owner_db))
    made = save(platform, scope="PLATFORM", instructions=GOOD, note="Second platform default")
    assert made.status_code == 201, made.text
    assert made.json()["version"]["version_no"] >= 2  # version 1 was seeded
    # It is saved but not in use until a platform admin activates it.
    tag = platform_template(platform)
    assert tag["active_version"]["version_no"] != made.json()["version"]["version_no"]


def test_a_coaching_with_its_own_prompt_is_offered_a_newer_platform_default(
    login: Callable[[str], Who], team: dict[str, Member], owner_db: Database
) -> None:
    editor = login(team["editor"].email)
    mine = save(editor, instructions=GOOD + "\nmine", note="Ours").json()
    template = template_of(editor, mine["template"]["id"])
    on = switch(editor, template, "activate", version_id=mine["version"]["id"]).json()
    assert on["update_available"] is None
    # A coaching that follows the default is offered nothing: it already uses the new one.
    follower = call(
        login(team["faculty"].email), "GET", PROMPTS, params={"operation": "SOLVE"}
    ).json()
    assert [t["scope"] for t in follower["data"]] == ["PLATFORM"]

    platform = login(platform_admin(owner_db))
    new = save(
        platform,
        scope="PLATFORM",
        instructions="Better. {{question}} {{syllabus}}",
        note="Improved",
    ).json()
    base = platform_template(platform)
    assert switch(platform, base, "activate", version_id=new["version"]["id"]).status_code == 200

    flagged = template_of(editor, on["id"])
    assert flagged["update_available"]["version_no"] == new["version"]["version_no"]
    assert flagged["update_available"]["change_note"] == "Improved"

    # Seen and declined: the flag goes, the coaching's text stays.
    kept = switch(editor, flagged, "dismiss-update")
    assert kept.status_code == 200
    assert kept.json()["update_available"] is None
    assert kept.json()["active_version"]["version_no"] == 1
    assert switch(editor, kept.json(), "dismiss-update").status_code == 409  # nothing left to see

    # A third default arrives; this time the coaching adopts it.
    third = save(
        platform, scope="PLATFORM", instructions="Best. {{question}} {{syllabus}}", note="Best"
    ).json()
    assert (
        switch(
            platform, platform_template(platform), "activate", version_id=third["version"]["id"]
        ).status_code
        == 200
    )
    flagged = template_of(editor, on["id"])
    adopted = switch(editor, flagged, "adopt-default")
    assert adopted.status_code == 200, adopted.text
    assert adopted.json()["update_available"] is None
    assert adopted.json()["active_version"]["version_no"] == 2  # a new coaching version
    version = call(
        editor, "GET", f"{PROMPTS}/versions/{adopted.json()['active_version']['id']}"
    ).json()
    assert version["instructions"] == "Best. {{question}} {{syllabus}}"
    assert version["change_note"] == (
        f"Adopted platform default version {third['version']['version_no']}"
    )
    assert switch(editor, adopted.json(), "adopt-default").status_code == 409


def test_resetting_follows_the_platform_so_no_update_is_shown_afterwards(
    login: Callable[[str], Who], team: dict[str, Member], owner_db: Database
) -> None:
    editor = login(team["editor"].email)
    mine = save(editor, operation="VERIFY", instructions="Check {{question}}").json()
    template = template_of(editor, mine["template"]["id"])
    on = switch(editor, template, "activate", version_id=mine["version"]["id"]).json()
    off = switch(editor, on, "reset").json()
    platform = login(platform_admin(owner_db))
    new = save(
        platform,
        scope="PLATFORM",
        operation="VERIFY",
        instructions="Check {{question}} well",
        note="n",
    ).json()
    switch(
        platform, platform_template(platform, "VERIFY"), "activate", version_id=new["version"]["id"]
    )
    assert template_of(editor, off["id"])["update_available"] is None


# --- Personal prompts -----------------------------------------------------------------------------


def test_a_personal_prompt_is_seen_by_its_author_and_admins_only(
    login: Callable[[str], Who], team: dict[str, Member]
) -> None:
    author = login(team["faculty"].email)
    other = login(team["other"].email)
    made = save(
        author,
        scope="PERSONAL",
        name="My strict check",
        operation="VERIFY",
        instructions="Be strict. {{question}}",
    )
    assert made.status_code == 201, made.text
    template = made.json()["template"]
    assert (template["scope"], template["name"]) == ("PERSONAL", "My strict check")
    assert template["owner_user_id"] == str(team["faculty"].user_id)

    mine = call(author, "GET", PROMPTS, params={"scope": "PERSONAL"}).json()["data"]
    assert [t["name"] for t in mine] == ["My strict check"]
    assert call(other, "GET", PROMPTS, params={"scope": "PERSONAL"}).json()["data"] == []
    for url in (
        f"{PROMPTS}/templates/{template['id']}",
        f"{PROMPTS}/templates/{template['id']}/versions",
        f"{PROMPTS}/versions/{made.json()['version']['id']}",
    ):
        assert call(other, "GET", url).status_code == 404
        assert call(author, "GET", url).status_code == 200
        assert call(login(team["admin"].email), "GET", url).status_code == 200
    seen = call(login(team["admin"].email), "GET", PROMPTS, params={"scope": "PERSONAL"}).json()
    assert [t["name"] for t in seen["data"]] == ["My strict check"]

    # Nobody else adds to it, and it is never "activated": it is chosen when running.
    assert (
        save(
            other,
            scope="PERSONAL",
            template_id=template["id"],
            operation="VERIFY",
            instructions="Hijack {{question}}",
        ).status_code
        == 404
    )
    assert (
        save(
            login(team["admin"].email),
            scope="PERSONAL",
            template_id=template["id"],
            operation="VERIFY",
            instructions="Edit {{question}}",
        ).status_code
        == 403
    )
    refused = switch(author, template, "activate", version_id=made.json()["version"]["id"])
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "AI_PROMPT_PERSONAL_NOT_ACTIVATED"


def test_personal_prompts_are_named_once_per_author_and_need_a_name(
    login: Callable[[str], Who], team: dict[str, Member]
) -> None:
    author = login(team["faculty"].email)
    other = login(team["other"].email)
    text_ = "Check {{question}}"
    assert save(author, scope="PERSONAL", operation="VERIFY", instructions=text_).status_code == 422
    first = save(author, scope="PERSONAL", operation="VERIFY", name="Strict", instructions=text_)
    again = save(
        author, scope="PERSONAL", operation="VERIFY", name="STRICT", instructions=text_ + " twice"
    )
    assert (
        again.json()["template"]["id"] == first.json()["template"]["id"]
    )  # same name, same prompt
    assert again.json()["version"]["version_no"] == 2
    theirs = save(other, scope="PERSONAL", operation="VERIFY", name="Strict", instructions=text_)
    assert theirs.json()["template"]["id"] != first.json()["template"]["id"]  # another person's own


def test_a_run_uses_a_personal_prompt_only_for_its_author(
    login: Callable[[str], Who], team: dict[str, Member], db: Database
) -> None:
    author = login(team["faculty"].email)
    made = save(
        author,
        scope="PERSONAL",
        name="Mine",
        operation="SOLVE",
        instructions="Solve it. {{question}}",
    ).json()
    save(
        author,
        scope="PERSONAL",
        name="Mine",
        operation="SOLVE",
        instructions="Solve it well. {{question}}",
    )
    template_id = UUID(made["template"]["id"])

    def resolve_as(member: Member, **kw: Any) -> prompts.Resolved:
        with db.transaction(context(member)) as session:
            return prompts.resolve(
                session,
                organization_id=member.org_id,
                user_id=member.user_id,
                operation=kw.pop("operation", Operation.SOLVE),
                **kw,
            )

    got = resolve_as(team["faculty"], personal_template_id=template_id)
    assert (got.source, got.instructions) == (
        "PERSONAL",
        "Solve it well. {{question}}",
    )  # the latest
    with pytest.raises(AppError) as hidden:
        resolve_as(team["other"], personal_template_id=template_id)
    assert hidden.value.status_code == 404
    with pytest.raises(AppError):  # an admin may read it but a run never borrows it
        resolve_as(team["admin"], personal_template_id=template_id)
    with pytest.raises(AppError):  # and it is for one operation only
        resolve_as(team["faculty"], personal_template_id=template_id, operation=Operation.TAG)


# --- A prompt typed for one run -------------------------------------------------------------------


def test_a_one_off_prompt_is_checked_and_stored_nowhere_in_the_library(
    team: dict[str, Member], db: Database, owner_db: Database
) -> None:
    def library_rows() -> tuple[int, int]:
        with owner_db.transaction(TenantContext(is_platform=True)) as session:
            return (
                session.scalar(select(func.count()).select_from(PromptTemplate)) or 0,
                session.scalar(select(func.count()).select_from(PromptVersion)) or 0,
            )

    before = library_rows()
    member = team["faculty"]
    with db.transaction(context(member)) as session:
        got = prompts.resolve(
            session,
            organization_id=member.org_id,
            user_id=member.user_id,
            operation=Operation.SOLVE,
            one_off="Think hard about {{question}}",
        )
        with pytest.raises(AppError) as invalid:
            prompts.resolve(
                session,
                organization_id=member.org_id,
                user_id=member.user_id,
                operation=Operation.SOLVE,
                one_off="No placeholder here",
            )
    assert (got.source, got.version_id) == ("ONE_OFF", None)
    assert got.instructions == "Think hard about {{question}}"
    assert len(got.content_hash) == 64
    assert invalid.value.code == "AI_PROMPT_INVALID"
    assert library_rows() == before


# --- Translation prompts per language -------------------------------------------------------------


def test_a_coaching_can_have_its_own_translation_prompt_for_one_language(
    login: Callable[[str], Who], team: dict[str, Member], db: Database
) -> None:
    editor = login(team["editor"].email)
    text_ = "Translate {{question}} into {{target_language}}"
    general = save(editor, operation="TRANSLATE", instructions=text_ + " plainly").json()
    tamil = save(
        editor, operation="TRANSLATE", instructions=text_ + " in Tamil style", target_language="ta"
    ).json()
    assert tamil["template"]["id"] != general["template"]["id"]
    assert tamil["template"]["target_language"] == "ta"
    for made in (general, tamil):
        template = template_of(editor, made["template"]["id"])
        assert (
            switch(editor, template, "activate", version_id=made["version"]["id"]).status_code
            == 200
        )

    def used(language: str | None) -> str:
        member = team["faculty"]
        with db.transaction(context(member)) as session:
            return prompts.resolve(
                session,
                organization_id=member.org_id,
                user_id=member.user_id,
                operation=Operation.TRANSLATE,
                language=language,
            ).instructions

    assert used("ta").endswith("in Tamil style")
    assert used("hi").endswith("plainly")  # no Hindi prompt: the coaching's general one
    assert used(None).endswith("plainly")

    assert (
        save(editor, operation="TRANSLATE", instructions=text_, target_language="xx").status_code
        == 422
    )
    assert save(editor, operation="TAG", target_language="ta").status_code == 422


# --- Comparing versions ---------------------------------------------------------------------------


def test_the_difference_between_two_versions_is_shown_line_by_line(
    login: Callable[[str], Who], team: dict[str, Member]
) -> None:
    editor = login(team["editor"].email)
    one = save(
        editor, instructions="Line A\n{{question}}\n{{syllabus}}\nLine C", temperature="0.2"
    ).json()
    two = save(
        editor, instructions="Line A\n{{question}}\n{{syllabus}}\nLine D\nLine E", temperature="0.4"
    ).json()
    result = call(
        editor,
        "GET",
        f"{PROMPTS}/diff",
        params={"from": one["version"]["id"], "to": two["version"]["id"]},
    ).json()
    assert result["changed"] is True
    assert [(line["op"], line["text"]) for line in result["lines"]] == [
        ("same", "Line A"),
        ("same", "{{question}}"),
        ("same", "{{syllabus}}"),
        ("removed", "Line C"),
        ("added", "Line D"),
        ("added", "Line E"),
    ]
    assert (result["temperature_from"], result["temperature_to"]) == ("0.20", "0.40")
    same = call(
        editor,
        "GET",
        f"{PROMPTS}/diff",
        params={"from": one["version"]["id"], "to": one["version"]["id"]},
    ).json()
    assert same["changed"] is False

    solve = save(editor, operation="SOLVE", instructions="Solve {{question}}").json()
    cross = call(
        editor,
        "GET",
        f"{PROMPTS}/diff",
        params={"from": one["version"]["id"], "to": solve["version"]["id"]},
    )
    assert cross.status_code == 422
    assert cross.json()["error"]["code"] == "AI_PROMPT_DIFF_MISMATCH"


def test_a_coaching_prompt_can_be_compared_with_the_platform_default(
    login: Callable[[str], Who], team: dict[str, Member]
) -> None:
    editor = login(team["editor"].email)
    mine = save(editor, instructions="Tag well.\n{{question}}\n{{syllabus}}").json()
    platform = platform_template(editor)
    result = call(
        editor,
        "GET",
        f"{PROMPTS}/diff",
        params={"from": platform["active_version"]["id"], "to": mine["version"]["id"]},
    )
    assert result.status_code == 200
    assert result.json()["changed"] is True


# --- Another coaching's prompts -------------------------------------------------------------------


def test_one_coachings_prompts_are_invisible_to_another(
    login: Callable[[str], Who], team: dict[str, Member], owner_db: Database
) -> None:
    mine = save(login(team["editor"].email), note="Private").json()
    stranger = make_member(owner_db, "ADMIN", coaching_name="Another Coaching")
    theirs = login(stranger.email)
    listed = call(theirs, "GET", PROMPTS).json()["data"]
    assert all(t["scope"] == "PLATFORM" for t in listed)
    assert call(theirs, "GET", f"{PROMPTS}/templates/{mine['template']['id']}").status_code == 404
    assert call(theirs, "GET", f"{PROMPTS}/versions/{mine['version']['id']}").status_code == 404
    other = save(theirs, instructions=GOOD + "\ntheirs").json()
    assert other["template"]["id"] != mine["template"]["id"]  # each coaching has its own prompt
    assert Decimal("1") == Decimal(other["version"]["version_no"])
