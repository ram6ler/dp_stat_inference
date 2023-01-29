# Inference on DP Statistics

A simple helper class to perform bootstrap-based statistical inference on grade data released by IB.

## To Install

```
python3 -m pip install git+https://github.com/ram6ler/dp_stat_inference@main
```

## To Use

The library exposes a `Subject` class that may be used to generate statistics, samples and confidence intervals on subjects based on grade boundaries and distributions [published by IB](https://ibo.org/about-the-ib/facts-and-figures/statistical-bulletins/diploma-programme-and-career-related-programme-statistical-bulletin/) shortly after each examination session.

Example use:

```py
import dpstats as dp

s = dp.Subject(
    # Arbitrary id.
    subject_id=11,
    # Subject name and level.
    name="Business Management",
    level="HL",
    # Boundary data published by IB.
    boundary_data={
        "1": (0, 14),
        "2": (15, 26),
        "3": (27, 37),
        "4": (38, 49),
        "5": (50, 56),
        "6": (57, 67),
        "7": (68, 100),
    },
    # Grade distribution data published by IB.
    distribution_data={
        "1": 0.002,
        "2": 0.021,
        "3": 0.073,
        "4": 0.212,
        "5": 0.201,
        "6": 0.308,
        "7": 0.183,
    },
)

# Estimated statistics of world scaled marks.
print(s.scaled_mean)  # 57.1235
print(s.scaled_standard_deviation)  # 16.1724147161146

# Estimated z-score for a given scaled mark.
s.z_score_for(50)  # -0.4404722563107392

# 95% confidence interval for average grade for 20 students.
print(s.average_grade_confidence_interval(20, 0.95))  # (4.65, 5.8)
```

## Why?

IB provides schools with school and world mean grades in each subject ostensibly so that they may may assess their own student group performance in each subject. Technically, while the grades from 1 to 7 used by IB happen to be expressed as numeric symbols, they form ordinal categoric data and might as meaningfully have been expressed as the symbols G to A, which makes statistics such as mean less meaningful when taken at face value, and difficult to compare as group performance measures. The fact is that IB grades mean different things between subjects, and even within a subject, students with very different performance levels (sometimes as great as a standard deviation) can be awarded the same grade (e.g. a student who just scrapes a 6 can have a very different level of mastery of the subject as the student who just misses a 7 may have), and a difference of 1 point can mean different things for different grades, even within a subject.

Many schools simply take the differences between their school means and the respective world means at face value; of those schools that do perform inferential analyses, many use inappropriate statistical tools meant for numeric data, such as t-tests, which do not take into account the difference in grade meaning between and within subjects.

This library allows us to easily perform Monte Carlo bootstrap sampling to perform inferential analyses. This technique makes no assumptions about the nature of the data: it randomly generates large numbers of samples of the specified number, based on the worldwide grade distributions of the a specified subject and level, and generates confidence intervals of that measurement.

While IB's practice of treating categorical data as if it were numerical data is questionable, expressions of the mean do provide some information about the performance of groups. Analyses based on bootstrapping the grade distributions published by IB (equivalent to sampling from the world population of IB students for a given year) allow us to better place those group statistics in context and determine the significance of observed differences.