class TaskContainer:
    """
    could be a playbook, could be a role task file
    """
    def __init__(self, name):
        self.name = name
        self._tasks = []
        self._variables = []

    def add_variable(self, key, value):
        self._variables.append({key: value})

    @property
    def variables(self):
        return self._variables
    
    @variables.setter 
    def variables(self,vegetables):
         self._variables = vegetables

    @property
    def tasks(self):
        return self._tasks
    
    @tasks.setter
    def tasks(self,tusks):
         self._tasks = tusks

    def add_task(self, task):
        self._tasks.append(task)

    def clear_tasks(self):
        self._tasks = []

    def empty(self):
        return len(self._tasks) == 0
