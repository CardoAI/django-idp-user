import requests
from django.conf import settings
from rest_framework import status


class OpaService:
    @staticmethod
    def upload_policy_to_opa():
        with open(settings.IDP_USER_APP['REGO_FILE_PATH']) as policy_file:
            opa_domain = settings.IDP_USER_APP['OPA_DOMAIN']
            opa_version = settings.IDP_USER_APP['OPA_VERSION']
            app_identifier = settings.IDP_USER_APP['APP_IDENTIFIER']
            url = f"http://{opa_domain}/{opa_version}/policies/{app_identifier}/{settings.APP_ENV}"

            print(f"Uploading policy to {url}...")

            # Replace APP_ENV in rego file to match the app environment
            payload = policy_file.read().replace("{{APP_ENV}}", settings.APP_ENV)
            response = requests.put(url, data=payload)

            if response.ok:
                print("Successfully uploaded policy")
            else:
                raise Exception(f"Could not upload policy!")

    @staticmethod
    def update_opa_data_through_idp(authorization_header):
        response = requests.post(
            url=f"http://{settings.IDP_USER_APP['IDP_URL']}/api/apps/update_opa_data/",
            json={'app': settings.IDP_USER_APP['APP_IDENTIFIER']},
            headers={
                "Authorization": authorization_header,
            }
        )

        if response != status.HTTP_204_NO_CONTENT:
            raise Exception("Cannot update OPA data through IDP!")

    @staticmethod
    def update_opa(authorization_header):
        OpaService.upload_policy_to_opa()
        OpaService.update_opa_data_through_idp(authorization_header)