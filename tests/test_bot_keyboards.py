"""Bot menu layout + the platform-aware plan-order signup button."""

from app.bots import keyboards, texts
from app.models import Platform


def test_main_menu_puts_register_and_order_side_by_side():
    first_row = keyboards.main_menu()["keyboard"][0]
    assert [b["text"] for b in first_row] == [
        texts.BTN_REGISTER_CLASS,
        texts.BTN_ORDER_PLAN,
    ]


def test_plan_signup_opens_a_mini_app_on_telegram():
    button = keyboards.plan_signup(Platform.TELEGRAM, "https://x.test/signup/")[
        "inline_keyboard"
    ][0][0]
    assert button["web_app"] == {"url": "https://x.test/signup/"}
    assert "url" not in button  # Mini App, not a plain link


def test_plan_signup_falls_back_to_a_url_button_on_bale():
    button = keyboards.plan_signup(Platform.BALE, "https://x.test/signup/")[
        "inline_keyboard"
    ][0][0]
    assert button["url"] == "https://x.test/signup/"
    assert "web_app" not in button  # Bale has no Mini App
