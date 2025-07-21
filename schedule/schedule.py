class Subject:
    def __init__(self):
        self.name = str
        self.publisher = str
        self.textbook = str
        self.scope = str

class Schedule:
    def __init__(self):
        self.week : int
        self.subjects = [] #Subject 넣으셈
        self.importance : int
        self.is_finished : bool