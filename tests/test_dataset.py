from eval.dataset import DATASET


def test_dataset_has_multiple_cases_with_topics_and_facts():
    assert len(DATASET) >= 5
    for case in DATASET:
        assert case.topic
        assert len(case.key_facts) >= 2
