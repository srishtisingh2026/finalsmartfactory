"""
Prompt Service - MLflow-Only Implementation
Uses MLflow Prompt Registry as the single source of truth.
Supports both local MLflow and Azure ML MLflow.
"""

import os
import re
import mlflow
from mlflow import MlflowClient
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)


def setup_azure_ml_auth():
    """
    Set up authentication and register Azure ML MLflow plugin.
    Must be called BEFORE setting MLflow tracking URI.
    """
    try:
        import azureml.mlflow
        logger.info("Azure ML MLflow plugin registered successfully")
        return True
    except ImportError as e:
        logger.error(f"Failed to import azureml-mlflow: {e}")
        logger.error("Install with: pip install azureml-mlflow")
        return False
    except Exception as e:
        logger.warning(f"Azure ML setup warning: {e}")
        return True


def setup_dagshub_auth():
    """
    Set up authentication for DagsHub MLflow.
    Ensures MLFLOW_TRACKING_USERNAME and MLFLOW_TRACKING_PASSWORD are set.
    """
    username = os.getenv("MLFLOW_TRACKING_USERNAME")
    password = os.getenv("MLFLOW_TRACKING_PASSWORD")

    if not username or not password:
        logger.error("DagsHub authentication requires MLFLOW_TRACKING_USERNAME and MLFLOW_TRACKING_PASSWORD")
        return False

    # Ensure environment variables are set for MLflow HTTP auth
    os.environ["MLFLOW_TRACKING_USERNAME"] = username
    os.environ["MLFLOW_TRACKING_PASSWORD"] = password

    logger.info(f"DagsHub authentication configured for user: {username}")
    return True


class PromptVersion(BaseModel):
    id: str
    name: str
    version: int
    content: str
    description: str
    variables: List[str]
    tags: List[str]
    model_parameters: Dict
    environment: str
    author: str
    created_at: datetime
    mlflow_run_id: Optional[str] = None


class PromptService:
    """
    Service for managing prompts using MLflow Prompt Registry.
    Single source of truth - no DuckDB mirroring.
    """

    def __init__(self):
        self.mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

        if self.mlflow_tracking_uri.startswith("azureml://"):
            logger.info("Detected Azure ML MLflow tracking URI")
            if not setup_azure_ml_auth():
                raise RuntimeError("Failed to set up Azure ML MLflow. Install azureml-mlflow package.")
        elif "dagshub.com" in self.mlflow_tracking_uri:
            logger.info("Detected DagsHub MLflow tracking URI")
            if not setup_dagshub_auth():
                raise RuntimeError("Failed to set up DagsHub MLflow. Set MLFLOW_TRACKING_USERNAME and MLFLOW_TRACKING_PASSWORD.")

        mlflow.set_tracking_uri(self.mlflow_tracking_uri)
        self.client = MlflowClient(tracking_uri=self.mlflow_tracking_uri)
        logger.info(f"MLflow tracking URI set to: {self.mlflow_tracking_uri}")

    def _sanitize_name_for_mlflow(self, name: str) -> str:
        """
        Sanitize prompt name for MLflow (only alphanumeric, hyphens, underscores, dots).
        Spaces are converted to hyphens. Case-insensitive (converted to lowercase).
        """
        sanitized = name.lower()
        sanitized = sanitized.replace(" ", "-")
        sanitized = re.sub(r'[^a-zA-Z0-9\-_.]', '', sanitized)
        sanitized = sanitized.strip('-')
        return sanitized

    def _find_actual_mlflow_name(self, name: str) -> Optional[str]:
        """
        Find the actual MLflow prompt name by matching case-insensitively.
        """
        sanitized = self._sanitize_name_for_mlflow(name)

        try:
            all_prompts = mlflow.genai.search_prompts()
            for prompt in all_prompts:
                if prompt.name.lower() == sanitized:
                    return prompt.name
            return None
        except Exception as e:
            logger.debug(f"Error searching for prompt name: {e}")
            return None

    def _get_prompt_version(self, prompt) -> int:
        """Extract version from MLflow prompt object."""
        if hasattr(prompt, 'version'):
            return int(prompt.version)
        elif hasattr(prompt, 'version_number'):
            return int(prompt.version_number)
        elif hasattr(prompt, 'latest_version'):
            return int(prompt.latest_version)
        elif isinstance(prompt, dict):
            return int(prompt.get('version', prompt.get('version_number', 1)))
        return 1

    def _get_prompt_template(self, prompt_version) -> str:
        """Extract template/content from MLflow PromptVersion object."""
        if hasattr(prompt_version, 'template'):
            return prompt_version.template
        elif hasattr(prompt_version, 'content'):
            return prompt_version.content
        elif hasattr(prompt_version, 'text'):
            return prompt_version.text
        elif hasattr(prompt_version, 'prompt'):
            return prompt_version.prompt
        elif hasattr(prompt_version, 'prompt_text'):
            return prompt_version.prompt_text
        elif isinstance(prompt_version, dict):
            return prompt_version.get('template', prompt_version.get('content', prompt_version.get('text', '')))

        logger.warning(f"Could not find template in prompt version object. Type: {type(prompt_version)}")
        return ""

    def _get_latest_version(self, name: str) -> int:
        """Get the latest version number for a prompt."""
        try:
            prompts = mlflow.genai.search_prompts(filter_string=f"name='{name}'")
            if prompts:
                prompt = prompts[0]
                if hasattr(prompt, 'latest_version'):
                    return int(prompt.latest_version)
                if hasattr(prompt, 'version'):
                    return int(prompt.version)
        except Exception as e:
            logger.debug(f"Could not get version from search: {e}")

        version = 1
        while True:
            try:
                mlflow.genai.load_prompt(f"prompts:/{name}/{version + 1}")
                version += 1
            except:
                break
            if version > 100:
                break

        return version

    def _fetch_prompt_with_template(self, name: str, version: int = None) -> tuple:
        """Fetch a prompt with its template using mlflow.genai.load_prompt()."""
        try:
            if version is None:
                version = self._get_latest_version(name)

            prompt_obj = mlflow.genai.load_prompt(f"prompts:/{name}/{version}")

            template = self._get_prompt_template(prompt_obj)
            tags = self._get_prompt_tags(prompt_obj)

            ver = version
            if hasattr(prompt_obj, 'version'):
                ver = int(prompt_obj.version)

            return template, ver, tags
        except Exception as e:
            logger.error(f"Failed to fetch prompt '{name}' version {version} with template: {e}")
            return "", version or 1, {}

    def _get_prompt_tags(self, prompt) -> Dict[str, str]:
        """Extract tags from MLflow prompt object."""
        if hasattr(prompt, 'tags') and prompt.tags:
            return prompt.tags
        elif hasattr(prompt, 'metadata') and prompt.metadata:
            return prompt.metadata
        elif isinstance(prompt, dict):
            return prompt.get('tags', prompt.get('metadata', {}))
        return {}

    def _extract_variables(self, content: str) -> List[str]:
        """Extract variables from prompt content (supports {{variable}} and {variable} formats)"""
        pattern = r'\{\{?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}?\}'
        variables = re.findall(pattern, content)
        return list(set(variables))

    def _format_tags_for_mlflow(self, tags: List[str], model_parameters: Dict, description: str = "", display_name: str = "") -> Dict[str, str]:
        """Convert tags list and model parameters to MLflow tags dictionary."""
        mlflow_tags = {}

        if description:
            mlflow_tags["description"] = description

        if display_name:
            mlflow_tags["display_name"] = display_name

        for key, value in model_parameters.items():
            mlflow_tags[key] = str(value)

        for tag in tags:
            mlflow_tags[f"tag_{tag}"] = "true"

        return mlflow_tags

    def _parse_mlflow_tags(self, mlflow_tags: Dict[str, str]) -> tuple[List[str], Dict[str, Any], str, str]:
        """Parse MLflow tags back to user tags list, model parameters, description, and display_name."""
        user_tags = []
        model_params = {}
        description = ""
        display_name = ""

        model_param_keys = {'model', 'temperature', 'maxTokens', 'topP', 'freqPenalty', 'presPenalty'}

        for key, value in (mlflow_tags or {}).items():
            if key == "description":
                description = value
            elif key == "display_name":
                display_name = value
            elif key.startswith("tag_"):
                user_tags.append(key[4:])
            elif key.startswith("mlflow."):
                continue
            elif key in model_param_keys:
                try:
                    if key in {'temperature', 'topP', 'freqPenalty', 'presPenalty'}:
                        model_params[key] = float(value)
                    elif key == 'maxTokens':
                        model_params[key] = int(value)
                    else:
                        model_params[key] = value
                except (ValueError, TypeError):
                    model_params[key] = value

        return user_tags, model_params, description, display_name

    def create_prompt_version(
        self,
        name: str,
        content: str,
        variables: List[str],
        tags: List[str] = None,
        description: str = "",
        model_parameters: Dict = None
    ) -> Dict:
        """Creates a new version of a prompt using MLflow Prompt Registry."""
        if tags is None:
            tags = []
        if model_parameters is None:
            model_parameters = {}

        display_name = name

        existing_name = self._find_actual_mlflow_name(name)
        if existing_name:
            mlflow_name = existing_name
        else:
            mlflow_name = self._sanitize_name_for_mlflow(name)

        if not variables:
            variables = self._extract_variables(content)

        mlflow_tags = self._format_tags_for_mlflow(tags, model_parameters, description, display_name)

        try:
            info = mlflow.genai.register_prompt(
                name=mlflow_name,
                template=content,
                tags=mlflow_tags
            )

            version = self._get_prompt_version(info)

            logger.info(f"Registered prompt '{mlflow_name}' (display: '{display_name}') version {version} in MLflow")

            return {
                "id": f"{mlflow_name}-v{version}",
                "name": display_name,
                "version": version,
                "status": "success",
                "variables": variables,
                "description": description
            }

        except Exception as e:
            logger.error(f"MLflow prompt registration failed: {e}")
            raise Exception(f"Failed to register prompt in MLflow: {str(e)}")

    def list_prompts(self) -> List[Dict]:
        """Returns the latest version of each distinct prompt from MLflow."""
        try:
            all_prompts = mlflow.genai.search_prompts()

            prompt_names = set()
            for prompt in all_prompts:
                prompt_names.add(prompt.name)

            prompts_list = []

            for mlflow_name in prompt_names:
                try:
                    template, version, version_tags = self._fetch_prompt_with_template(mlflow_name)

                    prompt_metadata = next((p for p in all_prompts if p.name == mlflow_name), None)
                    metadata_tags = self._get_prompt_tags(prompt_metadata) if prompt_metadata else {}

                    all_tags = {**metadata_tags, **version_tags}

                    user_tags, model_params, description, display_name = self._parse_mlflow_tags(all_tags)

                    name = display_name if display_name else mlflow_name

                    if not description and prompt_metadata and hasattr(prompt_metadata, 'description'):
                        description = prompt_metadata.description or ""

                    environment = "dev"
                    if prompt_metadata and hasattr(prompt_metadata, 'aliases') and prompt_metadata.aliases:
                        if 'production' in prompt_metadata.aliases or 'prod' in prompt_metadata.aliases:
                            environment = "production"

                    prompts_list.append({
                        "id": f"{mlflow_name}-v{version}",
                        "name": name,
                        "description": description,
                        "tags": [environment] + user_tags,
                        "latest_version": version,
                        "version": version,
                        "content": template,
                        "model_parameters": model_params,
                        "variables": self._extract_variables(template)
                    })

                except Exception as e:
                    logger.error(f"Failed to fetch prompt '{mlflow_name}': {e}")
                    continue

            logger.info(f"Retrieved {len(prompts_list)} prompts from MLflow")
            return prompts_list

        except Exception as e:
            logger.error(f"Failed to fetch prompts from MLflow: {e}")
            return []

    def get_prompt_by_name(self, name: str, version: Optional[int] = None) -> Optional[Dict]:
        """Get a specific prompt by name and optionally version."""
        try:
            mlflow_name = self._find_actual_mlflow_name(name)
            if not mlflow_name:
                mlflow_name = self._sanitize_name_for_mlflow(name)

            template, prompt_version, version_tags = self._fetch_prompt_with_template(mlflow_name, version)

            if not template and not version_tags:
                return None

            all_prompts = mlflow.genai.search_prompts(filter_string=f"name='{mlflow_name}'")
            prompt_metadata = all_prompts[0] if all_prompts else None

            metadata_tags = self._get_prompt_tags(prompt_metadata) if prompt_metadata else {}
            all_tags = {**metadata_tags, **version_tags}

            user_tags, model_params, description, display_name = self._parse_mlflow_tags(all_tags)

            final_name = display_name if display_name else mlflow_name

            if not description and prompt_metadata and hasattr(prompt_metadata, 'description'):
                description = prompt_metadata.description or ""

            environment = "dev"
            if prompt_metadata and hasattr(prompt_metadata, 'aliases') and prompt_metadata.aliases:
                if 'production' in prompt_metadata.aliases or 'prod' in prompt_metadata.aliases:
                    environment = "production"

            created_at = datetime.utcnow().isoformat()
            if prompt_metadata and hasattr(prompt_metadata, 'creation_timestamp') and prompt_metadata.creation_timestamp:
                created_at = prompt_metadata.creation_timestamp.isoformat()

            return {
                "id": f"{mlflow_name}-v{prompt_version}",
                "name": final_name,
                "version": prompt_version,
                "content": template,
                "description": description,
                "variables": self._extract_variables(template),
                "tags": user_tags,
                "model_parameters": model_params,
                "environment": environment,
                "created_at": created_at
            }

        except Exception as e:
            logger.error(f"Failed to get prompt '{name}': {e}")
            return None

    def get_history(self, prompt_name: str) -> List[Dict]:
        """Fetches all versions of a prompt from MLflow."""
        try:
            mlflow_name = self._find_actual_mlflow_name(prompt_name)
            if not mlflow_name:
                logger.warning(f"No prompt found matching '{prompt_name}'")
                return []

            prompt_metadata_list = mlflow.genai.search_prompts(filter_string=f"name='{mlflow_name}'")

            if not prompt_metadata_list:
                logger.warning(f"No versions found for prompt '{mlflow_name}'")
                return []

            prompt_metadata = prompt_metadata_list[0]

            latest_version = self._get_latest_version(mlflow_name)

            history = []

            for ver_num in range(1, latest_version + 1):
                try:
                    template, version, version_tags = self._fetch_prompt_with_template(mlflow_name, ver_num)

                    metadata_tags = self._get_prompt_tags(prompt_metadata)
                    all_tags = {**metadata_tags, **version_tags}

                    user_tags, model_params, description, display_name = self._parse_mlflow_tags(all_tags)

                    if not description and hasattr(prompt_metadata, 'description'):
                        description = prompt_metadata.description or ""

                    environment = "dev"
                    if hasattr(prompt_metadata, 'aliases') and prompt_metadata.aliases:
                        if 'production' in prompt_metadata.aliases or 'prod' in prompt_metadata.aliases:
                            environment = "production"

                    created_at = ""
                    if hasattr(prompt_metadata, 'creation_timestamp') and prompt_metadata.creation_timestamp:
                        try:
                            created_at = prompt_metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M")
                        except:
                            created_at = str(prompt_metadata.creation_timestamp)

                    history.append({
                        "version": version,
                        "date": created_at,
                        "author": "admin",
                        "comment": description or f"Version {version}",
                        "environment": environment,
                        "content": template,
                        "model_parameters": model_params,
                        "variables": self._extract_variables(template)
                    })

                except Exception as e:
                    logger.warning(f"Could not fetch version {ver_num} of '{mlflow_name}': {e}")
                    continue

            history.sort(key=lambda x: x['version'], reverse=True)

            logger.info(f"Retrieved {len(history)} versions for prompt '{mlflow_name}'")
            return history

        except Exception as e:
            logger.error(f"Failed to get history for prompt '{prompt_name}': {e}")
            return []

    def promote_version(self, prompt_name: str, version: int, target_env: str) -> bool:
        """Promotes a version to an environment using MLflow aliases."""
        try:
            mlflow_name = self._find_actual_mlflow_name(prompt_name)
            if not mlflow_name:
                mlflow_name = self._sanitize_name_for_mlflow(prompt_name)

            mlflow.genai.set_prompt_alias(
                name=mlflow_name,
                alias=target_env,
                version=version
            )

            logger.info(f"Promoted '{mlflow_name}' v{version} to '{target_env}'")
            return True

        except Exception as e:
            logger.error(f"Failed to promote prompt: {e}")
            raise Exception(f"Failed to promote prompt: {str(e)}")


# Singleton instance
prompt_service = PromptService()
