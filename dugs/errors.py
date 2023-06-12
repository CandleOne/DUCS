from dugs.database import Company


class TieError(Exception):
    def __init__(self, *companies: Company) -> None:
        self.company1, self.company2 = companies
