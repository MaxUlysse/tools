#!/usr/bin/env python
""" Tests covering the pipeline schema code.
"""

import nf_core.schema

import click
import json
import mock
import os
import pytest
import requests
import shutil
import tempfile
import unittest
import yaml


class TestSchema(unittest.TestCase):
    """Class for schema tests"""

    def setUp(self):
        """ Create a new PipelineSchema object """
        self.schema_obj = nf_core.schema.PipelineSchema()
        self.root_repo_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        # Copy the template to a temp directory so that we can use that for tests
        self.template_dir = os.path.join(tempfile.mkdtemp(), "wf")
        template_dir = os.path.join(self.root_repo_dir, "nf_core", "pipeline-template", "{{cookiecutter.name_noslash}}")
        shutil.copytree(template_dir, self.template_dir)
        self.template_schema = os.path.join(self.template_dir, "nextflow_schema.json")

    def test_load_lint_schema(self):
        """ Check linting with the pipeline template directory """
        self.schema_obj.get_schema_path(self.template_dir)
        self.schema_obj.load_lint_schema()

    @pytest.mark.xfail(raises=AssertionError)
    def test_load_lint_schema_nofile(self):
        """ Check that linting raises properly if a non-existant file is given """
        self.schema_obj.get_schema_path("fake_file")
        self.schema_obj.load_lint_schema()

    @pytest.mark.xfail(raises=AssertionError)
    def test_load_lint_schema_notjson(self):
        """ Check that linting raises properly if a non-JSON file is given """
        self.schema_obj.get_schema_path(os.path.join(self.template_dir, "nextflow.config"))
        self.schema_obj.load_lint_schema()

    @pytest.mark.xfail(raises=AssertionError)
    def test_load_lint_schema_invalidjson(self):
        """ Check that linting raises properly if a JSON file is given with an invalid schema """
        # Make a temporary file to write schema to
        tmp_file = tempfile.NamedTemporaryFile()
        with open(tmp_file.name, "w") as fh:
            json.dump({"type": "fubar"}, fh)
        self.schema_obj.get_schema_path(tmp_file.name)
        self.schema_obj.load_lint_schema()

    def test_get_schema_path_dir(self):
        """ Get schema file from directory """
        self.schema_obj.get_schema_path(self.template_dir)

    def test_get_schema_path_path(self):
        """ Get schema file from a path """
        self.schema_obj.get_schema_path(self.template_schema)

    @pytest.mark.xfail(raises=AssertionError)
    def test_get_schema_path_path_notexist(self):
        """ Get schema file from a path """
        self.schema_obj.get_schema_path("fubar", local_only=True)

    # TODO - Update when we do have a released pipeline with a valid schema
    @pytest.mark.xfail(raises=AssertionError)
    def test_get_schema_path_name(self):
        """ Get schema file from the name of a remote pipeline """
        self.schema_obj.get_schema_path("atacseq")

    @pytest.mark.xfail(raises=AssertionError)
    def test_get_schema_path_name_notexist(self):
        """
        Get schema file from the name of a remote pipeline
        that doesn't have a schema file
        """
        self.schema_obj.get_schema_path("exoseq")

    def test_load_schema(self):
        """ Try to load a schema from a file """
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.load_schema()

    def test_save_schema(self):
        """ Try to save a schema """
        # Load the template schema
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.load_schema()

        # Make a temporary file to write schema to
        tmp_file = tempfile.NamedTemporaryFile()
        self.schema_obj.schema_filename = tmp_file.name
        self.schema_obj.save_schema()

    def test_load_input_params_json(self):
        """ Try to load a JSON file with params for a pipeline run """
        # Make a temporary file to write schema to
        tmp_file = tempfile.NamedTemporaryFile()
        with open(tmp_file.name, "w") as fh:
            json.dump({"input": "fubar"}, fh)
        self.schema_obj.load_input_params(tmp_file.name)

    def test_load_input_params_yaml(self):
        """ Try to load a YAML file with params for a pipeline run """
        # Make a temporary file to write schema to
        tmp_file = tempfile.NamedTemporaryFile()
        with open(tmp_file.name, "w") as fh:
            yaml.dump({"input": "fubar"}, fh)
        self.schema_obj.load_input_params(tmp_file.name)

    @pytest.mark.xfail(raises=AssertionError)
    def test_load_input_params_invalid(self):
        """ Check failure when a non-existent file params file is loaded """
        self.schema_obj.load_input_params("fubar")

    def test_validate_params_pass(self):
        """ Try validating a set of parameters against a schema """
        # Load the template schema
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.load_schema()
        self.schema_obj.flatten_schema()
        self.schema_obj.input_params = {"input": "fubar"}
        assert self.schema_obj.validate_params()

    def test_validate_params_fail(self):
        """ Check that False is returned if params don't validate against a schema """
        # Load the template schema
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.load_schema()
        self.schema_obj.flatten_schema()
        self.schema_obj.input_params = {"fubar": "input"}
        assert not self.schema_obj.validate_params()

    def test_validate_schema_pass(self):
        """ Check that the schema validation passes """
        # Load the template schema
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.load_schema()
        self.schema_obj.flatten_schema()
        self.schema_obj.validate_schema(self.schema_obj.schema)

    @pytest.mark.xfail(raises=AssertionError)
    def test_validate_schema_fail_notjsonschema(self):
        """ Check that the schema validation fails when not JSONSchema """
        self.schema_obj.schema = {"type": "invalidthing"}
        self.schema_obj.validate_schema(self.schema_obj.schema)

    @pytest.mark.xfail(raises=AssertionError)
    def test_validate_schema_fail_nfcore(self):
        """
        Check that the schema validation fails nf-core addons

        An empty object {} is valid JSON Schema, but we want to have
        at least a 'properties' key, so this should fail with nf-core specific error.
        """
        self.schema_obj.schema = {}
        self.schema_obj.validate_schema(self.schema_obj.schema)

    def test_make_skeleton_schema(self):
        """ Test making a new schema skeleton """
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.pipeline_manifest["name"] = "nf-core/test"
        self.schema_obj.pipeline_manifest["description"] = "Test pipeline"
        self.schema_obj.make_skeleton_schema()
        self.schema_obj.validate_schema(self.schema_obj.schema)

    def test_get_wf_params(self):
        """ Test getting the workflow parameters from a pipeline """
        self.schema_obj.schema_filename = self.template_schema
        self.schema_obj.get_wf_params()

    def test_prompt_remove_schema_notfound_config_returntrue(self):
        """ Remove unrecognised params from the schema """
        self.schema_obj.pipeline_params = {"foo": "bar"}
        self.schema_obj.no_prompts = True
        assert self.schema_obj.prompt_remove_schema_notfound_config("baz")

    def test_prompt_remove_schema_notfound_config_returnfalse(self):
        """ Do not remove unrecognised params from the schema """
        self.schema_obj.pipeline_params = {"foo": "bar"}
        self.schema_obj.no_prompts = True
        assert not self.schema_obj.prompt_remove_schema_notfound_config("foo")

    def test_remove_schema_notfound_configs(self):
        """ Remove unrecognised params from the schema """
        self.schema_obj.schema = {"properties": {"foo": {"type": "string"}}, "required": ["foo"]}
        self.schema_obj.pipeline_params = {"bar": True}
        self.schema_obj.no_prompts = True
        params_removed = self.schema_obj.remove_schema_notfound_configs()
        assert len(self.schema_obj.schema["properties"]) == 0
        assert len(params_removed) == 1
        assert "foo" in params_removed

    def test_remove_schema_notfound_configs_childobj(self):
        """
        Remove unrecognised params from the schema,
        even when they're in a group
        """
        self.schema_obj.schema = {
            "properties": {"parent": {"type": "object", "properties": {"foo": {"type": "string"}}, "required": ["foo"]}}
        }
        self.schema_obj.pipeline_params = {"bar": True}
        self.schema_obj.no_prompts = True
        params_removed = self.schema_obj.remove_schema_notfound_configs()
        assert len(self.schema_obj.schema["properties"]["parent"]["properties"]) == 0
        assert len(params_removed) == 1
        assert "foo" in params_removed

    def test_add_schema_found_configs(self):
        """ Try adding a new parameter to the schema from the config """
        self.schema_obj.pipeline_params = {"foo": "bar"}
        self.schema_obj.schema = {"properties": {}}
        self.schema_obj.no_prompts = True
        params_added = self.schema_obj.add_schema_found_configs()
        assert len(self.schema_obj.schema["properties"]) == 1
        assert len(params_added) == 1
        assert "foo" in params_added

    def test_build_schema_param_str(self):
        """ Build a new schema param from a config value (string) """
        param = self.schema_obj.build_schema_param("foo")
        assert param == {"type": "string", "default": "foo"}

    def test_build_schema_param_bool(self):
        """ Build a new schema param from a config value (bool) """
        param = self.schema_obj.build_schema_param("True")
        print(param)
        assert param == {"type": "boolean", "default": True}

    def test_build_schema_param_int(self):
        """ Build a new schema param from a config value (int) """
        param = self.schema_obj.build_schema_param("12")
        assert param == {"type": "integer", "default": 12}

    def test_build_schema_param_int(self):
        """ Build a new schema param from a config value (float) """
        param = self.schema_obj.build_schema_param("12.34")
        assert param == {"type": "number", "default": 12.34}

    def test_build_schema(self):
        """
        Build a new schema param from a pipeline
        Run code to ensure it doesn't crash. Individual functions tested separately.
        """
        param = self.schema_obj.build_schema(self.template_dir, True, False, None)

    def test_build_schema_from_scratch(self):
        """
        Build a new schema param from a pipeline with no existing file
        Run code to ensure it doesn't crash. Individual functions tested separately.

        Pretty much a copy of test_launch.py test_make_pipeline_schema
        """
        test_pipeline_dir = os.path.join(tempfile.mkdtemp(), "wf")
        shutil.copytree(self.template_dir, test_pipeline_dir)
        os.remove(os.path.join(test_pipeline_dir, "nextflow_schema.json"))

        param = self.schema_obj.build_schema(test_pipeline_dir, True, False, None)

    @pytest.mark.xfail(raises=AssertionError)
    @mock.patch("requests.post")
    def test_launch_web_builder_timeout(self, mock_post):
        """ Mock launching the web builder, but timeout on the request """
        # Define the behaviour of the request get mock
        mock_post.side_effect = requests.exceptions.Timeout()
        self.schema_obj.launch_web_builder()

    @pytest.mark.xfail(raises=AssertionError)
    @mock.patch("requests.post")
    def test_launch_web_builder_connection_error(self, mock_post):
        """ Mock launching the web builder, but get a connection error """
        # Define the behaviour of the request get mock
        mock_post.side_effect = requests.exceptions.ConnectionError()
        self.schema_obj.launch_web_builder()

    @pytest.mark.xfail(raises=AssertionError)
    @mock.patch("requests.post")
    def test_get_web_builder_response_timeout(self, mock_post):
        """ Mock checking for a web builder response, but timeout on the request """
        # Define the behaviour of the request get mock
        mock_post.side_effect = requests.exceptions.Timeout()
        self.schema_obj.launch_web_builder()

    @pytest.mark.xfail(raises=AssertionError)
    @mock.patch("requests.post")
    def test_get_web_builder_response_connection_error(self, mock_post):
        """ Mock checking for a web builder response, but get a connection error """
        # Define the behaviour of the request get mock
        mock_post.side_effect = requests.exceptions.ConnectionError()
        self.schema_obj.launch_web_builder()

    def mocked_requests_post(**kwargs):
        """ Helper function to emulate POST requests responses from the web """

        class MockResponse:
            def __init__(self, data, status_code):
                self.status_code = status_code
                self.content = json.dumps(data)

        if kwargs["url"] == "invalid_url":
            return MockResponse({}, 404)

        if kwargs["url"] == "valid_url_error":
            response_data = {"status": "error", "api_url": "foo", "web_url": "bar"}
            return MockResponse(response_data, 200)

        if kwargs["url"] == "valid_url_success":
            response_data = {"status": "recieved", "api_url": "https://nf-co.re", "web_url": "https://nf-co.re"}
            return MockResponse(response_data, 200)

    @mock.patch("requests.post", side_effect=mocked_requests_post)
    def test_launch_web_builder_404(self, mock_post):
        """ Mock launching the web builder """
        self.schema_obj.web_schema_build_url = "invalid_url"
        try:
            self.schema_obj.launch_web_builder()
        except AssertionError as e:
            assert e.args[0] == "Could not access remote API results: invalid_url (HTML 404 Error)"

    @mock.patch("requests.post", side_effect=mocked_requests_post)
    def test_launch_web_builder_invalid_status(self, mock_post):
        """ Mock launching the web builder """
        self.schema_obj.web_schema_build_url = "valid_url_error"
        try:
            self.schema_obj.launch_web_builder()
        except AssertionError as e:
            assert e.args[0].startswith("JSON Schema builder response not recognised")

    @mock.patch("requests.post", side_effect=mocked_requests_post)
    @mock.patch("requests.get")
    @mock.patch("webbrowser.open")
    def test_launch_web_builder_success(self, mock_post, mock_get, mock_webbrowser):
        """ Mock launching the web builder """
        self.schema_obj.web_schema_build_url = "valid_url_success"
        try:
            self.schema_obj.launch_web_builder()
        except AssertionError as e:
            # Assertion error comes from get_web_builder_response() function
            assert e.args[0].startswith("Could not access remote API results: https://nf-co.re")

    def mocked_requests_get(*args, **kwargs):
        """ Helper function to emulate GET requests responses from the web """

        class MockResponse:
            def __init__(self, data, status_code):
                self.status_code = status_code
                self.content = json.dumps(data)

        if args[0] == "invalid_url":
            return MockResponse({}, 404)

        if args[0] == "valid_url_error":
            response_data = {"status": "error", "message": "testing"}
            return MockResponse(response_data, 200)

        if args[0] == "valid_url_waiting":
            response_data = {"status": "waiting_for_user", "message": "testing"}
            return MockResponse(response_data, 200)

        if args[0] == "valid_url_saved":
            response_data = {"status": "web_builder_edited", "message": "testing", "schema": {"foo": "bar"}}
            return MockResponse(response_data, 200)

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_get_web_builder_response_404(self, mock_post):
        """ Mock launching the web builder """
        self.schema_obj.web_schema_build_api_url = "invalid_url"
        try:
            self.schema_obj.get_web_builder_response()
        except AssertionError as e:
            assert e.args[0] == "Could not access remote API results: invalid_url (HTML 404 Error)"

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_get_web_builder_response_error(self, mock_post):
        """ Mock launching the web builder """
        self.schema_obj.web_schema_build_api_url = "valid_url_error"
        try:
            self.schema_obj.get_web_builder_response()
        except AssertionError as e:
            assert e.args[0].startswith("Got error from JSON Schema builder")

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_get_web_builder_response_waiting(self, mock_post):
        """ Mock launching the web builder """
        self.schema_obj.web_schema_build_api_url = "valid_url_waiting"
        assert self.schema_obj.get_web_builder_response() is False

    @mock.patch("requests.get", side_effect=mocked_requests_get)
    def test_get_web_builder_response_saved(self, mock_post):
        """ Mock launching the web builder """
        self.schema_obj.web_schema_build_api_url = "valid_url_saved"
        try:
            self.schema_obj.get_web_builder_response()
        except AssertionError as e:
            # Check that this is the expected AssertionError, as there are seveal
            assert e.args[0].startswith("Response from JSON Builder did not pass validation")
        assert self.schema_obj.schema == {"foo": "bar"}
