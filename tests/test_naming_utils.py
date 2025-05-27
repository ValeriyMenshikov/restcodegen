import pytest

from restcodegen.generator.naming import NamingUtils


@pytest.mark.parametrize(
    "value, expected",
    [
        ("user_id", "user_id"),
        ("user-id", "user_id"),
        ("userId", "user_id"),
        ("user id", "user_id"),
        ("User ID", "user_id"),
        ("User-ID", "user_id"),
        ("User.ID", "user_id"),
        ("User/ID", "user_id"),
        ("user/id", "user_id"),
        ("user.id", "user_id"),
        ("UserID", "user_id"),
        ("API", "api"),
        ("API2", "api2"),
        ("2FA", "2fa"),
        ("SMZ", "smz"),
        ("SMZv2", "smzv2"),
        ("v2API", "v2_api"),
        ("v2", "v2"),
        ("v1_resend_SMZ_status_check_response", "v1_resend_smz_status_check_response"),
        ("campaignv2_list_search_promo_products_response_1p", "campaignv2_list_search_promo_products_response_1p"),
        ("test_with_multiple_abbreviations_SMZ_API_2FA", "test_with_multiple_abbreviations_smz_api_2fa"),
        ("UserLoginByIDRequest", "user_login_by_id_request"),
    ],
)
def test_to_snake_case(value: str, expected: str) -> None:
    assert NamingUtils.to_snake_case(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("user_id", "UserId"),
        ("user-id", "UserId"),
        ("userId", "UserId"),
        ("user id", "UserId"),
        ("User ID", "UserId"),
        ("User-ID", "UserId"),
        ("User.ID", "UserId"),
        ("User/ID", "UserId"),
        ("user/id", "UserId"),
        ("user.id", "UserId"),
        ("UserID", "UserID"),
        ("API", "API"),
        ("API2", "API2"),
        ("2FA", "2FA"),
        ("SMZ", "SMZ"),
        ("SMZv2", "SMZv2"),
        ("v2API", "V2API"),
        ("v2", "V2"),
        ("v1_resend_SMZ_status_check_response", "V1ResendSMZStatusCheckResponse"),
        ("campaignv2_list_search_promo_products_response_1p", "Campaignv2ListSearchPromoProductsResponse1p"),
        ("test_with_multiple_abbreviations_SMZ_API_2FA", "TestWithMultipleAbbreviationsSMZAPI2FA"),
        ("UserLoginByIDRequest", "UserLoginByIDRequest"),
    ],
)
def test_to_pascal_case(value: str, expected: str) -> None:
    assert NamingUtils.to_pascal_case(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("user_id", "userId"),
        ("user-id", "userId"),
        ("userId", "userId"),
        ("user id", "userId"),
        ("User ID", "userId"),
        ("User-ID", "userId"),
        ("User.ID", "userId"),
        ("User/ID", "userId"),
        ("user/id", "userId"),
        ("user.id", "userId"),
        ("UserID", "userID"),
        ("API", "api"),
        ("API2", "api2"),
        ("2FA", "2fa"),
        ("SMZ", "smz"),
        ("SMZv2", "smzv2"),
        ("v2API", "v2API"),
        ("v2", "v2"),
        ("v1_resend_SMZ_status_check_response", "v1ResendSMZStatusCheckResponse"),
        ("campaignv2_list_search_promo_products_response_1p", "campaignv2ListSearchPromoProductsResponse1p"),
        ("test_with_multiple_abbreviations_SMZ_API_2FA", "testWithMultipleAbbreviationsSMZAPI2FA"),
        ("UserLoginByIDRequest", "userLoginByIDRequest"),
    ],
)
def test_to_camel_case(value: str, expected: str) -> None:
    assert NamingUtils.to_camel_case(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("user_id", "user_id"),
        ("class", "class_"),
        ("type", "type_"),
        ("object", "object_"),
        ("dict", "dict_"),
        ("list", "list_"),
        ("set", "set_"),
        ("id", "id_"),
        ("filter", "filter_"),
        ("map", "map_"),
        ("max", "max_"),
        ("min", "min_"),
        ("sum", "sum_"),
        ("API", "api"),
        ("API2", "api2"),
        ("2FA", "2fa"),
        ("SMZ", "smz"),
    ],
)
def test_to_param_name(value: str, expected: str) -> None:
    assert NamingUtils.to_param_name(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("user_id", "UserId"),
        ("user-id", "UserId"),
        ("userId", "UserId"),
        ("user id", "UserId"),
        ("User ID", "UserId"),
        ("User-ID", "UserId"),
        ("User.ID", "UserId"),
        ("User/ID", "UserId"),
        ("user/id", "UserId"),
        ("user.id", "UserId"),
        ("UserID", "UserID"),
        ("API", "API"),
        ("API2", "API2"),
        ("2FA", "2FA"),
        ("SMZ", "SMZ"),
    ],
)
def test_to_class_name(value: str, expected: str) -> None:
    assert NamingUtils.to_class_name(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("int", "int"),
        ("str", "str"),
        ("bool", "bool"),
        ("float", "float"),
        ("list", "list"),
        ("dict", "dict"),
        ("tuple", "tuple"),
        ("set", "set"),
        ("Any", "Any"),
        ("None", "None"),
    ],
)
def test_to_type_annotation(value: str, expected: str) -> None:
    assert NamingUtils.to_type_annotation(value) == expected
