from sqlite3 import connect
from random import random
from math import sqrt


def _tile(data: list[int | float], p: float) -> float:
    """
    Returns the p-tile value in `data`.
    Assumes data is sorted.
    """
    assert 0 <= p < 1
    d = p * (len(data) - 1)
    k = int(d)
    r = d - k

    return data[k] + r * (data[k + 1] - data[k])


def _convert_bounds(
    data: dict[str, tuple[int, int]] | str
) -> dict[str, tuple[int, int]]:
    """
    A helper that parses the bounds data if it is a string (for example
    if stored as text in a sqlite database).
    """
    match data:
        case str(data):
            result = eval(data)
        case dict(data):
            result = data
        case data:
            raise ValueError(f"Parse error: f{data!r}")
    return result


def _convert_distribution(data: dict[str, float] | str) -> dict[str, float]:
    """
    A helper that parses the bounds data if it is a string (for example
    if stored as text in a sqlite database).
    """
    match data:
        case str(data):
            result = {k: float(v) for k, v in eval(data).items()}
        case dict(data):
            result = data
        case data:
            raise ValueError(f"Parse error: f{data!r}")
    return result


class Subject:
    """
    A convenience class for storing subject statistics such as grade boundaries and
    distributions (published in the relevant statistical bulletin) and for estimating
    the scaled mark mean and standard deviation to facilitate more detailed analyses.

    Example:
    ```
    # Data obtained from published statistics bulletin.
    s = Subject(
      subject_id=11,
      name="Business Management",
      level="HL",
      boundary_data={
        '1': (0, 14),
        '2': (15, 26),
        '3': (27, 37),
        '4': (38, 49),
        '5': (50, 56),
        '6': (57, 67),
        '7': (68, 100)
      },
      distribution_data={
        '1': 0.002,
        '2': 0.021,
        '3': 0.073,
        '4': 0.212,
        '5': 0.201,
        '6': 0.308,
        '7': 0.183
      }
    )
    # Estimated statistics of world scaled marks.
    print(s.scaled_mean) # 57.1235
    print(s.scaled_standard_deviation) # 16.1724147161146

    # Estimated z-score for a given scaled mark.
    s.z_score_for(50) # -0.4404722563107392

    # 95% confidence interval for average grade for 20 students.
    print(s.average_grade_confidence_interval(20, 0.95)) # (4.65, 5.8)
    ```
    """

    def __init__(
        self,
        subject_id: int,
        name: str,
        level: str,
        boundary_data: dict[str, tuple[int, int]] | str,
        distribution_data: dict[str, float] | str,
    ) -> None:
        self.subject_id = subject_id
        self.name = name
        self.level = level
        self.boundaries = _convert_bounds(boundary_data)
        self.distribution = _convert_distribution(distribution_data)

        # Sometimes IB's numbers don't quite add up...
        total = sum(self.distribution.values())
        self._grades = sorted(self.distribution.keys())
        for grade in self._grades:
            self.distribution[grade] /= total

        self._memory: dict[str, float] = {}

    def random_grade(self) -> str:
        """
        Returns a random grade using the grade distribution
        as probability weights.
        """
        r = random()
        for grade in self._grades:
            r -= self.distribution[grade]
            if r < 0:
                break
        return grade

    def random_grade_sample(self, n: int) -> list[str]:
        """
        Returns a random sample of grades of size `n`, using
        the grade distribution as probability weights.
        """
        return [self.random_grade() for _ in range(n)]

    def bootstrap_grade_average(
        self, n: int, transform=lambda grade: float(grade)
    ) -> float:
        """
        Returns the mean of a bootstrap sample of size `n`. If grades cannot
        be interpreted numerically, `transform`, which maps the string grades
        to a numeric interpretation must be defined.
        """
        return sum(transform(grade) for grade in self.random_grade_sample(n)) / n

    def average_grade_confidence_interval(
        self, n: int, p: float, simulations=10_000
    ) -> tuple[float, float]:
        """
        Returns a bootstrapped `p`-confidence interval of the mean grade based
        on the sample size `n` and the world grade distributions.
        """
        assert 0 <= p < 1
        sampled_means = sorted(
            self.bootstrap_grade_average(n) for _ in range(simulations)
        )
        return _tile(sampled_means, 0.5 - p / 2), _tile(sampled_means, 0.5 + p / 2)

    def _midpoint(self, grade: str) -> float:
        lower, upper = self.boundaries[grade]
        return (lower + upper) / 2.0

    @property
    def scaled_mean(self) -> float:
        """
        Returns the world mean scaled marks, estimated from the grade
        boundaries and proportions.
        """
        key = "_mu"
        if key not in self._memory:

            self._memory[key] = sum(
                self._midpoint(grade) * self.distribution[grade]
                for grade in self._grades
            )
        return self._memory[key]

    @property
    def scaled_standard_deviation(self) -> float:
        """
        Returns the world standard deviation in scaled marks, estimated
        from the grade boundaries and proportions.
        """
        key = "_sigma"
        if key not in self._memory:

            self._memory[key] = sqrt(
                sum(
                    (self._midpoint(grade) - self.scaled_mean) ** 2
                    * self.distribution[grade]
                    for grade in self._grades
                )
            )
        return self._memory[key]

    def z_score_for(self, scaled_mark: int | float) -> float:
        """
        Returns the number of standard deviations `scaled_mark` is above the mean.
        """
        return (scaled_mark - self.scaled_mean) / self.scaled_standard_deviation

    def __repr__(self) -> str:
        return f"""
Subject(
    subject_id={self.subject_id},
    name='{self.name}',
    level='{self.level}',
    boundary_data="{self.boundaries}",
    distribution_data="{self.distribution}",
)
"""


def generate_subjects_from_sqlite_db(db_path: str) -> dict[int, Subject]:
    """
    Generates a `Subject` object for each row in a sqlite
    table. Expects the table to be of the form:

    ```text
        .----------------------.
        |Subject               |
        :----------------------:
        |id (PK) INTEGER       |
        |name TEXT             |
        |level TEXT            |
        |boundary_data TEXT    |
        |distribution_data TEXT|
        '----------------------'
    ```

    where `boundary_data` may be interpreted as a `dict[str, tuple[int, int]]`
    and `distribution_data` may be interpreted as a `dict[str, float]`.
    """

    with connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM Subject;")

        subjects: dict[int, Subject] = {}
        for row in cursor.fetchall():
            subject = Subject(*row)
            subjects[subject.subject_id] = subject

    return subjects
