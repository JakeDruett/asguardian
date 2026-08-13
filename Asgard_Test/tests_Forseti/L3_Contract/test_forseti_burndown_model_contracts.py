"""L3 Contract tests for remaining Forseti pydantic models (Phase 2.2 burn-down).

Covers Forseti-owned models that lacked L3 contract coverage per
_scripts/list_pydantic_models.py: Alignment, AsyncAPI/Avro/Database/JSONSchema/
OpenAPI/Protobuf base models, Compatibility, Contracts, Documentation, GraphQL,
LiveContract, MockServer, OpenAPI completeness, Reporting, and Rules.
"""
import pytest
from pydantic import ValidationError

from Asgard.Forseti.Alignment.models.alignment_models import (
    AlignmentConfig,
    AlignmentReport,
    DirectionEdge,
    EntityBinding,
    EntitySource,
)
from Asgard.Forseti.Alignment.models.ir_models import (
    IRField,
    IRRecord,
    IRType,
    SourceRef,
)
from Asgard.Forseti.AsyncAPI.models._asyncapi_base_models import (
    AsyncAPIValidationError,
    MessageInfo,
    OperationInfo,
    ServerInfo,
)
from Asgard.Forseti.Avro.models._avro_base_models import (
    AvroValidationError,
)
from Asgard.Forseti.CodeGen.models.codegen_models import (
    MethodDefinition,
)
from Asgard.Forseti.Compatibility.models.compat_models import (
    CompatReport,
    ImpactAssessment,
    UnifiedChange,
    UsageStats,
)
from Asgard.Forseti.Compatibility.models.legacy_models import (
    LegacyBreakingChange,
)
from Asgard.Forseti.Contracts.models.contract_models import (
    LifecycleMeta,
    VersionRecommendation,
)
from Asgard.Forseti.Database.models._database_base_models import (
    ConstraintDefinition,
)
from Asgard.Forseti.Database.models.database_models import (
    SchemaChange,
)
from Asgard.Forseti.Documentation.models._docs_base_models import (
    SchemaInfo,
    TagGroup,
)
from Asgard.Forseti.Documentation.models.docs_models import (
    DocumentationStructure,
)
from Asgard.Forseti.GraphQL.models.graphql_models import (
    GraphQLArgument,
    GraphQLDirective,
    GraphQLValidationError,
)
from Asgard.Forseti.JSONSchema.models._jsonschema_base_models import (
    JSONSchemaValidationError,
)
from Asgard.Forseti.JSONSchema.models.jsonschema_models import (
    DialectConversionResult,
    LLMCompatibilityIssue,
    LLMCompatibilityResult,
    LossRecord,
)
from Asgard.Forseti.LiveContract.models.live_contract_models import (
    DriftReport,
    ProbeConfig,
    ProbeOperation,
    ProbePlan,
    ProbeResult,
    Workflow,
    WorkflowReport,
    WorkflowStep,
    WorkflowStepResult,
)
from Asgard.Forseti.MockServer.models._mock_base_models import (
    MockHeader,
    MockParameter,
    MockRequestBody,
)
from Asgard.Forseti.MockServer.models.mock_models import (
    MockDataResult,
    MockServerGenerationResult,
)
from Asgard.Forseti.OpenAPI.models._openapi_base_models import (
    OpenAPIContact,
    OpenAPILicense,
    OpenAPIServer,
    OpenAPIValidationError,
)
from Asgard.Forseti.OpenAPI.models.completeness_models import (
    CompletenessReport,
    CompletenessSignals,
    CompletenessVector,
    GateResult,
)
from Asgard.Forseti.OpenAPI.models.openapi_models import (
    OpenAPIOperation,
    OpenAPIParameter,
    OpenAPIPath,
    OpenAPIRequestBody,
    OpenAPIResponse,
    OpenAPISchema,
    OpenAPISecurityScheme,
)
from Asgard.Forseti.Protobuf.models._protobuf_base_models import (
    ProtobufEnum,
    ProtobufService,
    ProtobufValidationError,
)
from Asgard.Forseti.Protobuf.models.protobuf_models import (
    ProtobufCompatibilityResult,
)
from Asgard.Forseti.Reporting.models.finding_models import (
    Coordinates,
    Finding,
    Remediation,
    ReportEnvelope,
    ReportSummary,
)
from Asgard.Forseti.Rules.models.rule_models import (
    BaselineEntry,
    ForsetiConfig,
    PathOverride,
    Profile,
    RuleMeta,
    SuppressionEntry,
    WaiverEntry,
)

# ---------------------------------------------------------------------------
# Asgard.Forseti.Alignment.models.alignment_models
# ---------------------------------------------------------------------------

class TestAlignmentConfigContract:
    def test_instantiates_with_defaults(self):
        obj = AlignmentConfig()
        assert obj is not None

    def test_round_trip(self):
        obj = AlignmentConfig()
        assert AlignmentConfig.model_validate(obj.model_dump()) == obj

class TestAlignmentReportContract:
    def test_instantiates_with_defaults(self):
        obj = AlignmentReport()
        assert obj is not None

    def test_round_trip(self):
        obj = AlignmentReport()
        assert AlignmentReport.model_validate(obj.model_dump()) == obj

class TestDirectionEdgeContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            DirectionEdge()

    def test_accepts_valid_data(self):
        obj = DirectionEdge(from_source="x", to_source="x")
        assert isinstance(obj, DirectionEdge)

    def test_round_trip(self):
        obj = DirectionEdge(from_source="x", to_source="x")
        assert DirectionEdge.model_validate(obj.model_dump()) == obj

class TestEntityBindingContract:
    def test_instantiates_with_defaults(self):
        obj = EntityBinding()
        assert obj is not None

    def test_round_trip(self):
        obj = EntityBinding()
        assert EntityBinding.model_validate(obj.model_dump()) == obj

class TestEntitySourceContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            EntitySource()

    def test_accepts_valid_data(self):
        obj = EntitySource(file="x")
        assert isinstance(obj, EntitySource)

    def test_round_trip(self):
        obj = EntitySource(file="x")
        assert EntitySource.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Alignment.models.ir_models
# ---------------------------------------------------------------------------

class TestIRFieldContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            IRField()

    def test_accepts_valid_data(self):
        obj = IRField(raw_name="x", type=IRType(type_class='bool'))
        assert isinstance(obj, IRField)

    def test_round_trip(self):
        obj = IRField(raw_name="x", type=IRType(type_class='bool'))
        assert IRField.model_validate(obj.model_dump()) == obj

class TestIRRecordContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            IRRecord()

    def test_accepts_valid_data(self):
        obj = IRRecord(name="x")
        assert isinstance(obj, IRRecord)

    def test_round_trip(self):
        obj = IRRecord(name="x")
        assert IRRecord.model_validate(obj.model_dump()) == obj

class TestIRTypeContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            IRType()

    def test_accepts_valid_data(self):
        obj = IRType(type_class='bool')
        assert isinstance(obj, IRType)

    def test_round_trip(self):
        obj = IRType(type_class='bool')
        assert IRType.model_validate(obj.model_dump()) == obj

class TestSourceRefContract:
    def test_instantiates_with_defaults(self):
        obj = SourceRef()
        assert obj is not None

    def test_round_trip(self):
        obj = SourceRef()
        assert SourceRef.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.AsyncAPI.models._asyncapi_base_models
# ---------------------------------------------------------------------------

class TestAsyncAPIValidationErrorContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            AsyncAPIValidationError()

    def test_accepts_valid_data(self):
        obj = AsyncAPIValidationError(path="x", message="x")
        assert isinstance(obj, AsyncAPIValidationError)

    def test_round_trip(self):
        obj = AsyncAPIValidationError(path="x", message="x")
        assert AsyncAPIValidationError.model_validate(obj.model_dump()) == obj

class TestMessageInfoContract:
    def test_instantiates_with_defaults(self):
        obj = MessageInfo()
        assert obj is not None

    def test_round_trip(self):
        obj = MessageInfo()
        assert MessageInfo.model_validate(obj.model_dump()) == obj

class TestOperationInfoContract:
    def test_instantiates_with_defaults(self):
        obj = OperationInfo()
        assert obj is not None

    def test_round_trip(self):
        obj = OperationInfo()
        assert OperationInfo.model_validate(obj.model_dump()) == obj

class TestServerInfoContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ServerInfo()

    def test_accepts_valid_data(self):
        obj = ServerInfo(url="x", protocol="x")
        assert isinstance(obj, ServerInfo)

    def test_round_trip(self):
        obj = ServerInfo(url="x", protocol="x")
        assert ServerInfo.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Avro.models._avro_base_models
# ---------------------------------------------------------------------------

class TestAvroValidationErrorContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            AvroValidationError()

    def test_accepts_valid_data(self):
        obj = AvroValidationError(path="x", message="x")
        assert isinstance(obj, AvroValidationError)

    def test_round_trip(self):
        obj = AvroValidationError(path="x", message="x")
        assert AvroValidationError.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.CodeGen.models.codegen_models
# ---------------------------------------------------------------------------

class TestMethodDefinitionContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MethodDefinition()

    def test_accepts_valid_data(self):
        obj = MethodDefinition(name="x", http_method="x", path="x")
        assert isinstance(obj, MethodDefinition)

    def test_round_trip(self):
        obj = MethodDefinition(name="x", http_method="x", path="x")
        assert MethodDefinition.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Compatibility.models.compat_models
# ---------------------------------------------------------------------------

class TestCompatReportContract:
    def test_instantiates_with_defaults(self):
        obj = CompatReport()
        assert obj is not None

    def test_round_trip(self):
        obj = CompatReport()
        assert CompatReport.model_validate(obj.model_dump()) == obj

class TestImpactAssessmentContract:
    def test_instantiates_with_defaults(self):
        obj = ImpactAssessment()
        assert obj is not None

    def test_round_trip(self):
        obj = ImpactAssessment()
        assert ImpactAssessment.model_validate(obj.model_dump()) == obj

class TestUnifiedChangeContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            UnifiedChange()

    def test_accepts_valid_data(self):
        obj = UnifiedChange(rule_id="x", format='openapi', message="x")
        assert isinstance(obj, UnifiedChange)

    def test_round_trip(self):
        obj = UnifiedChange(rule_id="x", format='openapi', message="x")
        assert UnifiedChange.model_validate(obj.model_dump()) == obj

class TestUsageStatsContract:
    def test_instantiates_with_defaults(self):
        obj = UsageStats()
        assert obj is not None

    def test_round_trip(self):
        obj = UsageStats()
        assert UsageStats.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Compatibility.models.legacy_models
# ---------------------------------------------------------------------------

class TestLegacyBreakingChangeContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            LegacyBreakingChange()

    def test_accepts_valid_data(self):
        obj = LegacyBreakingChange(change_type="x", path="x", message="x")
        assert isinstance(obj, LegacyBreakingChange)

    def test_round_trip(self):
        obj = LegacyBreakingChange(change_type="x", path="x", message="x")
        assert LegacyBreakingChange.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Contracts.models.contract_models
# ---------------------------------------------------------------------------

class TestLifecycleMetaContract:
    def test_instantiates_with_defaults(self):
        obj = LifecycleMeta()
        assert obj is not None

    def test_round_trip(self):
        obj = LifecycleMeta()
        assert LifecycleMeta.model_validate(obj.model_dump()) == obj

class TestVersionRecommendationContract:
    def test_instantiates_with_defaults(self):
        obj = VersionRecommendation()
        assert obj is not None

    def test_round_trip(self):
        obj = VersionRecommendation()
        assert VersionRecommendation.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Database.models._database_base_models
# ---------------------------------------------------------------------------

class TestConstraintDefinitionContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ConstraintDefinition()

    def test_accepts_valid_data(self):
        obj = ConstraintDefinition(name="x", table_name="x", constraint_type="x", definition="x")
        assert isinstance(obj, ConstraintDefinition)

    def test_round_trip(self):
        obj = ConstraintDefinition(name="x", table_name="x", constraint_type="x", definition="x")
        assert ConstraintDefinition.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Database.models.database_models
# ---------------------------------------------------------------------------

class TestSchemaChangeContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SchemaChange()

    def test_accepts_valid_data(self):
        obj = SchemaChange(change_type='add_table', table_name="x")
        assert isinstance(obj, SchemaChange)

    def test_round_trip(self):
        obj = SchemaChange(change_type='add_table', table_name="x")
        assert SchemaChange.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Documentation.models._docs_base_models
# ---------------------------------------------------------------------------

class TestSchemaInfoContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SchemaInfo()

    def test_accepts_valid_data(self):
        obj = SchemaInfo(name="x")
        assert isinstance(obj, SchemaInfo)

    def test_round_trip(self):
        obj = SchemaInfo(name="x")
        assert SchemaInfo.model_validate(obj.model_dump()) == obj

class TestTagGroupContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            TagGroup()

    def test_accepts_valid_data(self):
        obj = TagGroup(name="x")
        assert isinstance(obj, TagGroup)

    def test_round_trip(self):
        obj = TagGroup(name="x")
        assert TagGroup.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Documentation.models.docs_models
# ---------------------------------------------------------------------------

class TestDocumentationStructureContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            DocumentationStructure()

    def test_accepts_valid_data(self):
        obj = DocumentationStructure(title="x", version="x")
        assert isinstance(obj, DocumentationStructure)

    def test_round_trip(self):
        obj = DocumentationStructure(title="x", version="x")
        assert DocumentationStructure.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.GraphQL.models.graphql_models
# ---------------------------------------------------------------------------

class TestGraphQLArgumentContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            GraphQLArgument()

    def test_accepts_valid_data(self):
        obj = GraphQLArgument(name="x", type_name="x")
        assert isinstance(obj, GraphQLArgument)

    def test_round_trip(self):
        obj = GraphQLArgument(name="x", type_name="x")
        assert GraphQLArgument.model_validate(obj.model_dump()) == obj

class TestGraphQLDirectiveContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            GraphQLDirective()

    def test_accepts_valid_data(self):
        obj = GraphQLDirective(name="x")
        assert isinstance(obj, GraphQLDirective)

    def test_round_trip(self):
        obj = GraphQLDirective(name="x")
        assert GraphQLDirective.model_validate(obj.model_dump()) == obj

class TestGraphQLValidationErrorContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            GraphQLValidationError()

    def test_accepts_valid_data(self):
        obj = GraphQLValidationError(message="x")
        assert isinstance(obj, GraphQLValidationError)

    def test_round_trip(self):
        obj = GraphQLValidationError(message="x")
        assert GraphQLValidationError.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.JSONSchema.models._jsonschema_base_models
# ---------------------------------------------------------------------------

class TestJSONSchemaValidationErrorContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            JSONSchemaValidationError()

    def test_accepts_valid_data(self):
        obj = JSONSchemaValidationError(path="x", message="x")
        assert isinstance(obj, JSONSchemaValidationError)

    def test_round_trip(self):
        obj = JSONSchemaValidationError(path="x", message="x")
        assert JSONSchemaValidationError.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.JSONSchema.models.jsonschema_models
# ---------------------------------------------------------------------------

class TestDialectConversionResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            DialectConversionResult()

    def test_accepts_valid_data(self):
        obj = DialectConversionResult(converted={}, source_dialect="x", target_dialect="x")
        assert isinstance(obj, DialectConversionResult)

    def test_round_trip(self):
        obj = DialectConversionResult(converted={}, source_dialect="x", target_dialect="x")
        assert DialectConversionResult.model_validate(obj.model_dump()) == obj

class TestLLMCompatibilityIssueContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            LLMCompatibilityIssue()

    def test_accepts_valid_data(self):
        obj = LLMCompatibilityIssue(rule_id="x", path="x", message="x")
        assert isinstance(obj, LLMCompatibilityIssue)

    def test_round_trip(self):
        obj = LLMCompatibilityIssue(rule_id="x", path="x", message="x")
        assert LLMCompatibilityIssue.model_validate(obj.model_dump()) == obj

class TestLLMCompatibilityResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            LLMCompatibilityResult()

    def test_accepts_valid_data(self):
        obj = LLMCompatibilityResult(provider="x", is_compatible=True)
        assert isinstance(obj, LLMCompatibilityResult)

    def test_round_trip(self):
        obj = LLMCompatibilityResult(provider="x", is_compatible=True)
        assert LLMCompatibilityResult.model_validate(obj.model_dump()) == obj

class TestLossRecordContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            LossRecord()

    def test_accepts_valid_data(self):
        obj = LossRecord(path="x", keyword="x", message="x")
        assert isinstance(obj, LossRecord)

    def test_round_trip(self):
        obj = LossRecord(path="x", keyword="x", message="x")
        assert LossRecord.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.LiveContract.models.live_contract_models
# ---------------------------------------------------------------------------

class TestDriftReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            DriftReport()

    def test_accepts_valid_data(self):
        obj = DriftReport(base_url="x")
        assert isinstance(obj, DriftReport)

    def test_round_trip(self):
        obj = DriftReport(base_url="x")
        assert DriftReport.model_validate(obj.model_dump()) == obj

class TestProbeConfigContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ProbeConfig()

    def test_accepts_valid_data(self):
        obj = ProbeConfig(base_url="x")
        assert isinstance(obj, ProbeConfig)

    def test_round_trip(self):
        obj = ProbeConfig(base_url="x")
        assert ProbeConfig.model_validate(obj.model_dump()) == obj

class TestProbeOperationContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ProbeOperation()

    def test_accepts_valid_data(self):
        obj = ProbeOperation(operation_id="x", method="x", path="x")
        assert isinstance(obj, ProbeOperation)

    def test_round_trip(self):
        obj = ProbeOperation(operation_id="x", method="x", path="x")
        assert ProbeOperation.model_validate(obj.model_dump()) == obj

class TestProbePlanContract:
    def test_instantiates_with_defaults(self):
        obj = ProbePlan()
        assert obj is not None

    def test_round_trip(self):
        obj = ProbePlan()
        assert ProbePlan.model_validate(obj.model_dump()) == obj

class TestProbeResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ProbeResult()

    def test_accepts_valid_data(self):
        obj = ProbeResult(operation_id="x", method="x", path="x", request_url="x")
        assert isinstance(obj, ProbeResult)

    def test_round_trip(self):
        obj = ProbeResult(operation_id="x", method="x", path="x", request_url="x")
        assert ProbeResult.model_validate(obj.model_dump()) == obj

class TestWorkflowContract:
    def test_instantiates_with_defaults(self):
        obj = Workflow()
        assert obj is not None

    def test_round_trip(self):
        obj = Workflow()
        assert Workflow.model_validate(obj.model_dump()) == obj

class TestWorkflowReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            WorkflowReport()

    def test_accepts_valid_data(self):
        obj = WorkflowReport(base_url="x")
        assert isinstance(obj, WorkflowReport)

    def test_round_trip(self):
        obj = WorkflowReport(base_url="x")
        assert WorkflowReport.model_validate(obj.model_dump()) == obj

class TestWorkflowStepContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            WorkflowStep()

    def test_accepts_valid_data(self):
        obj = WorkflowStep(operation_id="x")
        assert isinstance(obj, WorkflowStep)

    def test_round_trip(self):
        obj = WorkflowStep(operation_id="x")
        assert WorkflowStep.model_validate(obj.model_dump()) == obj

class TestWorkflowStepResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            WorkflowStepResult()

    def test_accepts_valid_data(self):
        obj = WorkflowStepResult(operation_id="x")
        assert isinstance(obj, WorkflowStepResult)

    def test_round_trip(self):
        obj = WorkflowStepResult(operation_id="x")
        assert WorkflowStepResult.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.MockServer.models._mock_base_models
# ---------------------------------------------------------------------------

class TestMockHeaderContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MockHeader()

    def test_accepts_valid_data(self):
        obj = MockHeader(name="x", value="x")
        assert isinstance(obj, MockHeader)

    def test_round_trip(self):
        obj = MockHeader(name="x", value="x")
        assert MockHeader.model_validate(obj.model_dump()) == obj

class TestMockParameterContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MockParameter()

    def test_accepts_valid_data(self):
        obj = MockParameter(name="x", location="x")
        assert isinstance(obj, MockParameter)

    def test_round_trip(self):
        obj = MockParameter(name="x", location="x")
        assert MockParameter.model_validate(obj.model_dump()) == obj

class TestMockRequestBodyContract:
    def test_instantiates_with_defaults(self):
        obj = MockRequestBody()
        assert obj is not None

    def test_round_trip(self):
        obj = MockRequestBody()
        assert MockRequestBody.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.MockServer.models.mock_models
# ---------------------------------------------------------------------------

class TestMockDataResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MockDataResult()

    def test_accepts_valid_data(self):
        obj = MockDataResult(data="x", generation_strategy="x")
        assert isinstance(obj, MockDataResult)

    def test_round_trip(self):
        obj = MockDataResult(data="x", generation_strategy="x")
        assert MockDataResult.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.OpenAPI.models._openapi_base_models
# ---------------------------------------------------------------------------

class TestOpenAPIContactContract:
    def test_instantiates_with_defaults(self):
        obj = OpenAPIContact()
        assert obj is not None

    def test_round_trip(self):
        obj = OpenAPIContact()
        assert OpenAPIContact.model_validate(obj.model_dump()) == obj

class TestOpenAPILicenseContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            OpenAPILicense()

    def test_accepts_valid_data(self):
        obj = OpenAPILicense(name="x")
        assert isinstance(obj, OpenAPILicense)

    def test_round_trip(self):
        obj = OpenAPILicense(name="x")
        assert OpenAPILicense.model_validate(obj.model_dump()) == obj

class TestOpenAPIServerContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            OpenAPIServer()

    def test_accepts_valid_data(self):
        obj = OpenAPIServer(url="x")
        assert isinstance(obj, OpenAPIServer)

    def test_round_trip(self):
        obj = OpenAPIServer(url="x")
        assert OpenAPIServer.model_validate(obj.model_dump()) == obj

class TestOpenAPIValidationErrorContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            OpenAPIValidationError()

    def test_accepts_valid_data(self):
        obj = OpenAPIValidationError(path="x", message="x")
        assert isinstance(obj, OpenAPIValidationError)

    def test_round_trip(self):
        obj = OpenAPIValidationError(path="x", message="x")
        assert OpenAPIValidationError.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.OpenAPI.models.completeness_models
# ---------------------------------------------------------------------------

class TestCompletenessReportContract:
    def test_instantiates_with_defaults(self):
        obj = CompletenessReport()
        assert obj is not None

    def test_round_trip(self):
        obj = CompletenessReport()
        assert CompletenessReport.model_validate(obj.model_dump()) == obj

class TestCompletenessSignalsContract:
    def test_instantiates_with_defaults(self):
        obj = CompletenessSignals()
        assert obj is not None

    def test_round_trip(self):
        obj = CompletenessSignals()
        assert CompletenessSignals.model_validate(obj.model_dump()) == obj

class TestCompletenessVectorContract:
    def test_instantiates_with_defaults(self):
        obj = CompletenessVector()
        assert obj is not None

    def test_round_trip(self):
        obj = CompletenessVector()
        assert CompletenessVector.model_validate(obj.model_dump()) == obj

class TestGateResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            GateResult()

    def test_accepts_valid_data(self):
        obj = GateResult(tier='none', name="x")
        assert isinstance(obj, GateResult)

    def test_round_trip(self):
        obj = GateResult(tier='none', name="x")
        assert GateResult.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.OpenAPI.models.openapi_models
# ---------------------------------------------------------------------------

class TestOpenAPIOperationContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            OpenAPIOperation()

    def test_accepts_valid_data(self):
        obj = OpenAPIOperation(responses={})
        assert isinstance(obj, OpenAPIOperation)

    def test_round_trip(self):
        obj = OpenAPIOperation(responses={})
        assert OpenAPIOperation.model_validate(obj.model_dump()) == obj

class TestOpenAPIParameterContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            OpenAPIParameter()

    def test_accepts_valid_data(self):
        obj = OpenAPIParameter(name="x", location='query')
        assert isinstance(obj, OpenAPIParameter)

    def test_round_trip(self):
        obj = OpenAPIParameter(name="x", location='query')
        assert OpenAPIParameter.model_validate(obj.model_dump()) == obj

class TestOpenAPIPathContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            OpenAPIPath()

    def test_accepts_valid_data(self):
        obj = OpenAPIPath(path="x")
        assert isinstance(obj, OpenAPIPath)

    def test_round_trip(self):
        obj = OpenAPIPath(path="x")
        assert OpenAPIPath.model_validate(obj.model_dump()) == obj

class TestOpenAPIRequestBodyContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            OpenAPIRequestBody()

    def test_accepts_valid_data(self):
        obj = OpenAPIRequestBody(content={})
        assert isinstance(obj, OpenAPIRequestBody)

    def test_round_trip(self):
        obj = OpenAPIRequestBody(content={})
        assert OpenAPIRequestBody.model_validate(obj.model_dump()) == obj

class TestOpenAPIResponseContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            OpenAPIResponse()

    def test_accepts_valid_data(self):
        obj = OpenAPIResponse(description="x")
        assert isinstance(obj, OpenAPIResponse)

    def test_round_trip(self):
        obj = OpenAPIResponse(description="x")
        assert OpenAPIResponse.model_validate(obj.model_dump()) == obj

class TestOpenAPISchemaContract:
    def test_instantiates_with_defaults(self):
        obj = OpenAPISchema()
        assert obj is not None

    def test_round_trip(self):
        obj = OpenAPISchema()
        assert OpenAPISchema.model_validate(obj.model_dump()) == obj

class TestOpenAPISecuritySchemeContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            OpenAPISecurityScheme()

    def test_accepts_valid_data(self):
        obj = OpenAPISecurityScheme(type='apiKey')
        assert isinstance(obj, OpenAPISecurityScheme)

    def test_round_trip(self):
        obj = OpenAPISecurityScheme(type='apiKey')
        assert OpenAPISecurityScheme.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Protobuf.models._protobuf_base_models
# ---------------------------------------------------------------------------

class TestProtobufEnumContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ProtobufEnum()

    def test_accepts_valid_data(self):
        obj = ProtobufEnum(name="x")
        assert isinstance(obj, ProtobufEnum)

    def test_round_trip(self):
        obj = ProtobufEnum(name="x")
        assert ProtobufEnum.model_validate(obj.model_dump()) == obj

class TestProtobufServiceContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ProtobufService()

    def test_accepts_valid_data(self):
        obj = ProtobufService(name="x")
        assert isinstance(obj, ProtobufService)

    def test_round_trip(self):
        obj = ProtobufService(name="x")
        assert ProtobufService.model_validate(obj.model_dump()) == obj

class TestProtobufValidationErrorContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ProtobufValidationError()

    def test_accepts_valid_data(self):
        obj = ProtobufValidationError(path="x", message="x")
        assert isinstance(obj, ProtobufValidationError)

    def test_round_trip(self):
        obj = ProtobufValidationError(path="x", message="x")
        assert ProtobufValidationError.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Protobuf.models.protobuf_models
# ---------------------------------------------------------------------------

class TestProtobufCompatibilityResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ProtobufCompatibilityResult()

    def test_accepts_valid_data(self):
        obj = ProtobufCompatibilityResult(is_compatible=True, compatibility_level='full')
        assert isinstance(obj, ProtobufCompatibilityResult)

    def test_round_trip(self):
        obj = ProtobufCompatibilityResult(is_compatible=True, compatibility_level='full')
        assert ProtobufCompatibilityResult.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Reporting.models.finding_models
# ---------------------------------------------------------------------------

class TestCoordinatesContract:
    def test_instantiates_with_defaults(self):
        obj = Coordinates()
        assert obj is not None

    def test_round_trip(self):
        obj = Coordinates()
        assert Coordinates.model_validate(obj.model_dump()) == obj

class TestFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            Finding()

    def test_accepts_valid_data(self):
        obj = Finding(rule_id="x", severity='error', message="x")
        assert isinstance(obj, Finding)

    def test_round_trip(self):
        obj = Finding(rule_id="x", severity='error', message="x")
        assert Finding.model_validate(obj.model_dump()) == obj

class TestRemediationContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            Remediation()

    def test_accepts_valid_data(self):
        obj = Remediation(description="x")
        assert isinstance(obj, Remediation)

    def test_round_trip(self):
        obj = Remediation(description="x")
        assert Remediation.model_validate(obj.model_dump()) == obj

class TestReportEnvelopeContract:
    def test_instantiates_with_defaults(self):
        obj = ReportEnvelope()
        assert obj is not None

    def test_round_trip(self):
        obj = ReportEnvelope()
        assert ReportEnvelope.model_validate(obj.model_dump()) == obj

class TestReportSummaryContract:
    def test_instantiates_with_defaults(self):
        obj = ReportSummary()
        assert obj is not None

    def test_round_trip(self):
        obj = ReportSummary()
        assert ReportSummary.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Forseti.Rules.models.rule_models
# ---------------------------------------------------------------------------

class TestBaselineEntryContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            BaselineEntry()

    def test_accepts_valid_data(self):
        obj = BaselineEntry(fingerprint="x")
        assert isinstance(obj, BaselineEntry)

    def test_round_trip(self):
        obj = BaselineEntry(fingerprint="x")
        assert BaselineEntry.model_validate(obj.model_dump()) == obj

class TestForsetiConfigContract:
    def test_instantiates_with_defaults(self):
        obj = ForsetiConfig()
        assert obj is not None

    def test_round_trip(self):
        obj = ForsetiConfig()
        assert ForsetiConfig.model_validate(obj.model_dump()) == obj

class TestPathOverrideContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            PathOverride()

    def test_accepts_valid_data(self):
        obj = PathOverride(path="x")
        assert isinstance(obj, PathOverride)

    def test_round_trip(self):
        obj = PathOverride(path="x")
        assert PathOverride.model_validate(obj.model_dump()) == obj

class TestProfileContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            Profile()

    def test_accepts_valid_data(self):
        obj = Profile(name="x")
        assert isinstance(obj, Profile)

    def test_round_trip(self):
        obj = Profile(name="x")
        assert Profile.model_validate(obj.model_dump()) == obj

class TestRuleMetaContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            RuleMeta()

    def test_accepts_valid_data(self):
        obj = RuleMeta(rule_id="x", formats=set(), severity='error')
        assert isinstance(obj, RuleMeta)

    def test_round_trip(self):
        obj = RuleMeta(rule_id="x", formats=set(), severity='error')
        assert RuleMeta.model_validate(obj.model_dump()) == obj

class TestSuppressionEntryContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SuppressionEntry()

    def test_accepts_valid_data(self):
        obj = SuppressionEntry(rule="x")
        assert isinstance(obj, SuppressionEntry)

    def test_round_trip(self):
        obj = SuppressionEntry(rule="x")
        assert SuppressionEntry.model_validate(obj.model_dump()) == obj

class TestWaiverEntryContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            WaiverEntry()

    def test_accepts_valid_data(self):
        obj = WaiverEntry(rule="x", location="x", from_version="x", to_version="x", reason="x")
        assert isinstance(obj, WaiverEntry)

    def test_round_trip(self):
        obj = WaiverEntry(rule="x", location="x", from_version="x", to_version="x", reason="x")
        assert WaiverEntry.model_validate(obj.model_dump()) == obj



from Asgard.Forseti.MockServer.models.mock_models import (
    MockServerDefinition,
    MockServerGenerationResult,
)


class TestMockServerGenerationResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MockServerGenerationResult()

    def test_accepts_valid_data(self):
        defn = MockServerDefinition(title="x")
        obj = MockServerGenerationResult(success=True, server_definition=defn)
        assert isinstance(obj, MockServerGenerationResult)

    def test_round_trip(self):
        defn = MockServerDefinition(title="x")
        obj = MockServerGenerationResult(success=True, server_definition=defn)
        assert MockServerGenerationResult.model_validate(obj.model_dump()) == obj
