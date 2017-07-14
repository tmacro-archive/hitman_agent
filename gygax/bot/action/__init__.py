from .base import Action
from .command import	CommandAction, RegisterCommand, SetCommand, ReportCommand, ConfirmCommand, HelpCommand, HitsCommand, ResignCommand, RejoinCommand, TestCommand
from .ext import SlackAuthorizedAction
from .game import *
from .message import SendMessageAction, AssignmentNotifyAction, StructuredMessageAction, KillConfirmMessageAction
from .user import UpdateUserAction, ValidateSlackAction, CollectInfoAction, NewUserAction

actions = dict(
	commands = [
		CommandAction,
		RegisterCommand,
		SetCommand,
		ReportCommand,
		ConfirmCommand,
		HelpCommand,
		HitsCommand,
		ResignCommand,
		RejoinCommand,
		TestCommand,
	],
	external = [
		SlackAuthorizedAction
	],
	game = [
		MonitorFreeAction,
		SetupGameAction,
		LockUsersAction,
		AssignInitialHitsAction,
		StartGameAction,
		KillConfirmedAction,
		AssignNextRoundAction,
		CheckForWinnerAction,
		ConfirmKillAction,
		EndGameAction
	],
	message = [
		SendMessageAction,
		AssignmentNotifyAction,
		StructuredMessageAction,
		KillConfirmMessageAction
	],
	user = [
		UpdateUserAction,
		ValidateSlackAction,
		CollectInfoAction,
		NewUserAction
	]
)

all_actions = sum(actions.values(), [])