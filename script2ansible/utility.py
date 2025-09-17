class TaskContainer:
    """
    could be a playbook, could be a role task file
    """
    def __init__(self, name):
        self.name = name
        self.tasks = []
        self.variables = []

    def add_variable(self, key, value):
        breakpoint()
        self.variables.append({key: value})

    def add_task(self, task):
        self.tasks.append(task)

    def get_tasks(self):
        return self.tasks

    def clear_tasks(self):
        self.tasks = []

    def empty(self):
        return len(self.tasks) == 0
