import openai
from openai import InternalServerError, AuthenticationError

import logging

class AIPrReview:
    def __init__(
            self, 
            vio_api_key: list, 
            vio_base_url: str, 
            vio_model_name: str, 
            local_ai_api_key: str, 
            local_ai_base_url: str, 
            local_ai_model_name: str, 
            system_prompt: str = None
        ):
        self.vio_api_key = vio_api_key.split(',')
        self.vio_base_url = vio_base_url
        self.vio_model_name = vio_model_name

        self.local_ai_api_key = local_ai_api_key
        self.local_ai_base_url = local_ai_base_url
        self.local_ai_model_name = local_ai_model_name

        self.logger = logging.getLogger(__name__)
        self.messages = []

        # Add system prompt if provided
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def _call_local_model(self):
        """
        Call local model via ...
        """
        client = openai.OpenAI(
                api_key=self.local_ai_api_key,
                base_url=self.local_ai_base_url, 
            )
        
        try:
            response = client.chat.completions.create(
                model=self.local_ai_model_name,  # Local AI model name
                messages=self.messages
            )
            
            answer = response.choices[0].message.content

            return answer

        except AuthenticationError as e:
            self.logger.error(f"Local AI API AuthenticationError with API key {self.local_ai_api_key}: {e}", exc_info=True)  

        except InternalServerError as e:
            self.logger.error(f"Local AI API InternalServerError with API key {self.local_ai_api_key}: {e}", exc_info=True)
        
        except Exception as e:
            self.logger.error(f"Local AI API error with API key {self.local_ai_api_key}: {e}", exc_info=True)

        return None
     
    def _call_vio_model(self):
        """
        Call VIO via OpenAI API
        """

        for api_key in self.vio_api_key:
            client = openai.OpenAI(
                api_key=api_key,
                base_url=self.vio_base_url,  
                default_headers={
                    "useLegacyCompletionsEndpoint": "false",
                    "X-Tenant-ID": "default_tenant"
                }
            )

            try:
                response = client.chat.completions.create(
                    model=self.vio_model_name,  # VIO model name
                    messages=self.messages
                )
                
                answer = response.choices[0].message.content

                return answer

            except AuthenticationError as e:
                self.logger.error(f"VIO API AuthenticationError with API key {api_key}: {e}", exc_info=True)  

            except InternalServerError as e:
                self.logger.error(f"VIO API InternalServerError with API key {api_key}: {e}", exc_info=True)
            
            except Exception as e:
                self.logger.error(f"VIO API error with API key {api_key}: {e}", exc_info=True)

        return None

    def chat(self, question):
        # Add user question
        self.messages.append({"role": "user", "content": question})

        # Try VIO first
        result = self._call_vio_model()
        
        if result is not None:
            return result
        
        # Switch to local model
        else:
            self.logger.info("Get VIO response failed, switch to local model.")

            result = self._call_local_model()

            return result
