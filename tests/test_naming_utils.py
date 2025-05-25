import pytest

from restcodegen.generator.utils import NamingUtils


@pytest.mark.parametrize(
    "value, expected",
    [
        ("test_some_test", "test_some_test"),
        ("Test.Some.Test", "test_some_test"),
        ("Test/Some/Test", "test_some_test"),
        ("Test/SomeTest", "test_some_test"),
        ("Test Some Test", "test_some_test"),
        ("_test_some_test_", "test_some_test"),
        ("GET/mobile/orders/client/{client_id}", "get_mobile_orders_client_client_id"),
    ],
)
def test_to_snake_case(value: str, expected: str) -> None:
    assert NamingUtils.to_snake_case(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("test_some_test", "TestSomeTest"),
        ("dm-api-account", "DmApiAccount"),
        ("Test.Some.Test", "TestSomeTest"),
        ("Test/Some/Test", "TestSomeTest"),
        ("Test/SomeTest", "TestSomeTest"),
        ("Test Some Test", "TestSomeTest"),
        ("_test_some_test_", "TestSomeTest"),
        ("test_some_V3_test_", "TestSomeV3Test"),
        ("test_SomeV3_test_", "TestSomeV3Test"),
        ("ml_pipelineGetMetricsV1Response", "MlPipelineGetMetricsV1Response"),
        (
            "sc_v2GetOrderReservationGUIDByOrderIDResponse",
            "ScV2GetOrderReservationGUIDByOrderIDResponse",
        ),
        (
            "Ozon.Pvz.Api.Giveout.Grpc.GiveOutReportsApi",
            "OzonPvzApiGiveoutGrpcGiveOutReportsApi",
        ),
        (
            "userLoginByIDRequest",
            "UserLoginByIDRequest",
        ),
        # Тесты на аббревиатуры с цифрами
        (
            "v1_resend_SMZ_status_check_response",
            "V1ResendSMZStatusCheckResponse",
        ),
        (
            "campaignv2_list_search_promo_products_response_1p",
            "Campaignv2ListSearchPromoProductsResponse1P",
        ),
        (
            "api_v3_get_user_info_2FA_status",
            "ApiV3GetUserInfo2FAStatus",
        ),
        (
            "test_with_multiple_abbreviations_SMZ_API_2FA",
            "TestWithMultipleAbbreviationsSMZAPI2FA",
        ),
    ],
)
def test_to_pascal_case(value: str, expected: str) -> None:
    assert NamingUtils.to_pascal_case(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("test_some_test", "testSomeTest"),
        ("dm-api-account", "dmApiAccount"),
        ("Test.Some.Test", "testSomeTest"),
        ("Test/Some/Test", "testSomeTest"),
        ("Test/SomeTest", "testSomeTest"),
        ("Test Some Test", "testSomeTest"),
        ("_test_some_test_", "testSomeTest"),
        ("test_some_V3_test_", "testSomeV3Test"),
        ("test_SomeV3_test_", "testSomeV3Test"),
        ("ml_pipelineGetMetricsV1Response", "mlPipelineGetMetricsV1Response"),
        (
            "sc_v2GetOrderReservationGUIDByOrderIDResponse",
            "scV2GetOrderReservationGUIDByOrderIDResponse",
        ),
        (
            "Ozon.Pvz.Api.Giveout.Grpc.GiveOutReportsApi",
            "ozonPvzApiGiveoutGrpcGiveOutReportsApi",
        ),
        (
            "UserLoginByIDRequest",
            "userLoginByIDRequest",
        ),
        # Тесты на аббревиатуры с цифрами
        (
            "v1_resend_SMZ_status_check_response",
            "v1ResendSMZStatusCheckResponse",
        ),
        (
            "campaignv2_list_search_promo_products_response_1p",
            "campaignv2ListSearchPromoProductsResponse1P",
        ),
        (
            "api_v3_get_user_info_2FA_status",
            "apiV3GetUserInfo2FAStatus",
        ),
        (
            "test_with_multiple_abbreviations_SMZ_API_2FA",
            "testWithMultipleAbbreviationsSMZAPI2FA",
        ),
    ],
)
def test_to_camel_case(value: str, expected: str) -> None:
    assert NamingUtils.to_camel_case(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("test_some_test", "test_some_test"),
        ("testSomeTest", "test_some_test"),
        ("TestSomeTest", "test_some_test"),
        ("class", "class_"),
        ("for", "for_"),
        ("id", "id_"),
        ("type", "type_"),
    ],
)
def test_to_param_name(value: str, expected: str) -> None:
    assert NamingUtils.to_param_name(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("test_some_test", "TestSomeTest"),
        ("testSomeTest", "TestSomeTest"),
        ("TestSomeTest", "TestSomeTest"),
        ("class", "Class"),
        ("for", "For"),
        ("id", "Id"),
        ("type", "Type"),
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
        ("list", "list"),
        ("list[str]", "list[str]"),
        ("list[TestSomeTest]", "list[TestSomeTest]"),
        ("TestSomeTest", "TestSomeTest"),
        ("test_some_test", "TestSomeTest"),
    ],
)
def test_to_type_annotation(value: str, expected: str) -> None:
    assert NamingUtils.to_type_annotation(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("V1", True),
        ("API", True),
        ("SMZ", True),
        ("ID", True),
        ("1P", True),
        ("2FA", True),
        ("V2API", True),
        ("API2FA", True),
        ("Test", False),
        ("test", False),
        ("123", False),
        ("T", False),
    ],
)
def test_is_abbreviation(value: str, expected: bool) -> None:
    assert NamingUtils.is_abbreviation(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (
            "v1_resend_SMZ_status_check_response",
            ["v1", "resend", "SMZ", "status", "check", "response"],
        ),
        (
            "campaignv2_list_search_promo_products_response_1P",
            ["campaignv2", "list", "search", "promo", "products", "response", "1P"],
        ),
        (
            "test_with_multiple_abbreviations_SMZ_API_2FA",
            ["test", "with", "multiple", "abbreviations", "SMZ", "API", "2FA"],
        ),
        (
            "UserLoginByIDRequest",
            ["User", "Login", "By", "ID", "Request"],
        ),
    ],
)
def test_split_into_words(value: str, expected: list[str]) -> None:
    assert NamingUtils.split_into_words(value) == expected
