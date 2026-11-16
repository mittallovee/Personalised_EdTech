"""Review: the shared queue of questions waiting for QC, approval or publication (M4 note §3).

It decides who may see the queue and shapes the answer; the questions module owns the rows and the
visibility rule, and this module reaches them only through ``questions.public``.
"""
