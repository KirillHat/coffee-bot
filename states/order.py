"""FSM states for the multi-step checkout and admin flows."""
from aiogram.fsm.state import State, StatesGroup


class CheckoutStates(StatesGroup):
    full_name = State()
    phone = State()
    address = State()
    promo = State()
    confirm = State()


class AddProductStates(StatesGroup):
    category = State()
    name = State()
    description = State()
    price = State()
    photo_url = State()


class AddPromoStates(StatesGroup):
    code = State()
    discount = State()
    min_subtotal = State()
    max_uses = State()
