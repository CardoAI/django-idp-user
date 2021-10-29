package {{APP_IDENTIFIER}}.{{APP_ENV}}

import data.{{APP_IDENTIFIER}}.{{APP_ENV}}.roles_data

# By default, deny requests.
default allow = false

allow = true {
	some i, j, permission
	permission = roles_data[input.role][input.allowed_functionalities[i]][j]

    input.method == permission.method
    regex.match(permission.endpoint, input.path)
}
