from aiogram.fsm.state import State, StatesGroup


class AuthStates(StatesGroup):
    waiting_password = State()


class AddSaleStates(StatesGroup):
    waiting_amount = State()
    waiting_screenshots = State()


class AdminAddMemberStates(StatesGroup):
    waiting_role = State()
    waiting_name = State()


class AdminSalesHistoryStates(StatesGroup):
    waiting_user = State()
