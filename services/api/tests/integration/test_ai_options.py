"""M5 PR 5k-1: the short list a person may pick from in the run dialog (H-03, H-17).

Faculty cannot read the admin pages, so this is what the dialog is built on. It offers only what a
run would accept today, and never a key, a fallback or an admin's entry.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from qbank.core.tenancy import TenantContext
from qbank.modules.ai.models import AiModel
from tests.integration.ai_support import World
from tests.integration.conftest import make_member, sign_in

OPTIONS = "/api/v1/ai/options"


def get(world: World, headers: dict[str, str] | None = None) -> dict[str, object]:
    response = world.client.get(OPTIONS, headers=headers or world.author_headers)
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    return body


def listed(body: dict[str, object]) -> dict[str, dict[str, object]]:
    models: list[dict[str, object]] = body["models"]  # type: ignore[assignment]
    return {str(m["display_name"]): m for m in models}


def change(world: World, model_id: UUID, **fields: object) -> None:
    with world.owner_db.transaction(TenantContext(organization_id=world.org_id)) as session:
        row = session.scalars(select(AiModel).where(AiModel.id == model_id)).one()
        for name, value in fields.items():
            setattr(row, name, value)


def test_faculty_sees_the_enabled_model_with_its_price_and_the_operation_defaults(
    world: World,
) -> None:
    body = get(world)
    model = listed(body)["fake-small"]
    assert model["id"] == str(world.first_model)
    assert model["price_in_per_mtok"] == "1"
    assert model["price_out_per_mtok"] == "2"
    assert model["economy"] is False
    operations: list[dict[str, object]] = body["operations"]  # type: ignore[assignment]
    assert [o["operation"] for o in operations] == ["TAG", "TRANSLATE", "SOLVE", "VERIFY"]
    assert all(o["default_model_id"] == str(world.first_model) for o in operations)
    assert all(o["mode"] == "NOW" for o in operations)


def test_only_models_a_run_would_accept_are_offered(world: World) -> None:
    world.add_model("fake-off", enabled=False)
    gone = world.add_model("fake-gone")
    change(world, gone, available=False)
    plain = world.add_model("fake-no-json")
    change(world, plain, supports_json=False)
    assert set(listed(get(world))) == {"fake-small"}


def test_a_model_of_a_provider_without_a_key_is_not_offered(world: World) -> None:
    other = world.add_model("fake-other-provider")
    change(world, other, provider="ANTHROPIC")  # no Anthropic key is stored
    assert "fake-other-provider" not in listed(get(world))


def test_an_unknown_price_is_null_and_economy_needs_the_admin_to_allow_it(world: World) -> None:
    world.add_model("fake-unpriced", priced=False)
    world.add_model("fake-batch", batch=True, discount=Decimal("0.5"))
    models = listed(get(world))
    assert models["fake-unpriced"]["price_in_per_mtok"] is None
    assert models["fake-unpriced"]["economy"] is False
    assert models["fake-batch"]["economy"] is True


def test_a_default_that_cannot_be_used_any_more_is_not_offered_first(world: World) -> None:
    change(world, world.first_model, enabled=False)
    operations: list[dict[str, object]] = get(world)["operations"]  # type: ignore[assignment]
    assert all(o["default_model_id"] is None for o in operations)


def test_a_coaching_sees_only_its_own_models(world: World) -> None:
    stranger = make_member(world.owner_db, "FACULTY")
    headers = sign_in(world.client, stranger.email)
    body = get(world, headers)
    assert body["models"] == []
    operations: list[dict[str, object]] = body["operations"]  # type: ignore[assignment]
    assert all(o["default_model_id"] is None for o in operations)


def test_signing_in_is_required(world: World) -> None:
    anonymous = world.client.__class__(world.client.app)
    assert anonymous.get(OPTIONS).status_code == 401
