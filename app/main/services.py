from enum import Enum
from django_admin_logs.models import LogEntry
from django.contrib.contenttypes.models import ContentType

class ActionFlag(Enum):
    ADDITION = LogEntry.ADDITION
    CHANGE = LogEntry.CHANGE
    DELETION = LogEntry.DELETION

class LogAction:
    def __init__(self, user, model_instance, action: ActionFlag, change_message: str):
        self.user = user
        self.model_instance = model_instance
        self.action = action
        self.change_message = change_message

    def log(self):
        LogEntry.objects.log_action(
            user=self.user,
            content_type=ContentType.objects.get_for_model(self.model_instance),
            object_id=self.model_instance.pk,
            object_repr=str(self.model_instance),
            action_flag=self.action.value,
            change_message=self.change_message
        )
