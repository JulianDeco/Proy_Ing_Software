from enum import Enum
from django.contrib.admin.models import LogEntry

class ActionFlag(Enum):
    ADDITION = 1   
    CHANGE = 2    
    DELETION = 3   

class LogAction:
    def __init__(self, user, model_instance_or_queryset, action: ActionFlag, change_message: str):
        self.user = user
        self.target = model_instance_or_queryset
        self.action = action
        self.change_message = change_message

    def log(self):
        if not hasattr(self.target, '__iter__') or isinstance(self.target, dict):
            queryset = [self.target]
        else:
            queryset = self.target

        return LogEntry.objects.log_actions(
            user_id=self.user.pk if self.user else None,
            queryset=queryset,
            action_flag=self.action.value,
            change_message=self.change_message,
            single_object=len(queryset) == 1
        )
