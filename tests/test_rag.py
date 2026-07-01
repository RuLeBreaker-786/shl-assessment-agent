import unittest

from main import CATALOG, build_retrieval_index, retrieve_relevant_items


class RAGRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.catalog = CATALOG or []

    def test_retrieval_prefers_relevant_catalog_items(self):
        if not self.catalog:
            self.skipTest("Catalog data is not loaded")

        index = build_retrieval_index(self.catalog)
        results = retrieve_relevant_items("leadership personality manager", index=index, top_k=5)

        self.assertTrue(results, "Expected at least one relevant catalog item")
        self.assertEqual(results[0]["name"], "Global Skills Development Report")


if __name__ == "__main__":
    unittest.main()
