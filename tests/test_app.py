import unittest
from unittest.mock import Mock, patch

from bson import ObjectId

import app as application


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = application.create_app({"TESTING": True})
        cls.client = cls.app.test_client()

    def test_pages_render(self):
        for route in ["/", "/dashboard", "/analysis", "/prediction", "/history"]:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_analytics_are_derived_from_dataset(self):
        response = self.client.get("/api/analytics")
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        data = self.app.config["JOB_DATA"]
        self.assertEqual(result["stats"]["jobPostings"], len(data))
        self.assertEqual(result["stats"]["jobRoles"], data["job_title"].nunique())
        self.assertEqual(result["stats"]["countries"], data["country"].nunique())
        self.assertEqual(
            [item["skill"] for item in result["topProgrammingLanguages"]],
            ["SQL", "Python"],
        )
        self.assertEqual(sum(result["skillDemand"]["values"]), sum(
            int(data[column].fillna(0).gt(0).sum())
            for column in [
                "skills_python",
                "skills_sql",
                "skills_ml",
                "skills_deep_learning",
                "skills_cloud",
            ]
        ))

    def test_predict_rejects_unknown_role(self):
        response = self.client.post(
            "/api/predict",
            json={
                "jobRole": "Not a training role",
                "country": "Canada",
                "experienceLevel": "SE",
                "yearsExperience": 5,
                "skills": {
                    "python": True,
                    "sql": False,
                    "machineLearning": True,
                    "deepLearning": False,
                    "cloud": False,
                },
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("training dataset", response.get_json()["error"])

    def test_existing_model_predicts_with_dataset_feature_order(self):
        data = self.app.config["JOB_DATA"]
        with self.app.app_context():
            model = application.get_model()
            estimate = model.predict(data.loc[:0, application.EXPECTED_FEATURES])
            unknown_level = data.loc[:0, application.EXPECTED_FEATURES].copy()
            unknown_level.loc[unknown_level.index[0], "experience_level"] = "Executive"
            executive_estimate = model.predict(unknown_level)
        self.assertEqual(len(estimate), 1)
        self.assertGreater(float(estimate[0]), 0)
        self.assertGreater(float(executive_estimate[0]), 0)

    @patch("app.get_predictions_collection")
    def test_executive_history_filter_is_supported(self, get_collection):
        cursor = Mock()
        cursor.sort.return_value.limit.return_value = []
        get_collection.return_value.find.return_value = cursor
        response = self.client.get("/api/history?experienceLevel=Executive")
        self.assertEqual(response.status_code, 200)
        get_collection.return_value.find.assert_called_once_with(
            {"experienceLevel": "Executive"}
        )

    @patch("app.get_predictions_collection")
    @patch("app.get_model")
    def test_prediction_uses_model_feature_order_and_persists(self, get_model, get_collection):
        model = Mock()
        model.predict.return_value = [123456.78]
        get_model.return_value = model
        collection = Mock()
        collection.insert_one.side_effect = lambda record: record.update({"_id": ObjectId()})
        get_collection.return_value = collection
        data = self.app.config["JOB_DATA"]

        response = self.client.post(
            "/api/predict",
            json={
                "jobRole": data["job_title"].iloc[0],
                "country": data["country"].iloc[0],
                "experienceLevel": "EN",
                "yearsExperience": 3,
                "skills": {
                    "python": True,
                    "sql": False,
                    "machineLearning": True,
                    "deepLearning": False,
                    "cloud": False,
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        model.predict.assert_called_once()
        frame = model.predict.call_args.args[0]
        self.assertEqual(frame.columns.tolist(), application.EXPECTED_FEATURES)
        self.assertEqual(frame.iloc[0]["experience_level"], "Entry")
        collection.insert_one.assert_called_once()
        self.assertEqual(response.get_json()["prediction"]["predictedSalary"], 123456.78)
        self.assertNotIn("_id", response.get_json()["prediction"])


if __name__ == "__main__":
    unittest.main()
