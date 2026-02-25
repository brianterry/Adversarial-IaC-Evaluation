"""
Complete Experiment Infrastructure Stack

Single stack containing all resources:
- S3 bucket for experiment data
- IAM roles
- Lambda functions
- Step Functions state machines
- CloudWatch dashboard
"""

from pathlib import Path
from typing import Optional

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
    aws_iam as iam,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_logs as logs,
    aws_lambda as lambda_,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_cloudwatch as cloudwatch,
)
from constructs import Construct


class ExperimentStack(Stack):
    """Complete infrastructure for Adversarial IaC experiments."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment_name: str,
        notification_email: Optional[str] = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.environment_name = environment_name

        # Get the infrastructure directory
        infra_dir = Path(__file__).parent.parent.parent
        lambda_dir = infra_dir / "lambda"

        # =====================================================================
        # S3 BUCKET
        # =====================================================================
        self.bucket = s3.Bucket(
            self,
            "ExperimentBucket",
            bucket_name=f"{environment_name}-experiments-{self.account}",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="CleanupOldExperiments",
                    expiration=Duration.days(90),
                    noncurrent_version_expiration=Duration.days(30),
                )
            ],
        )

        # =====================================================================
        # SNS TOPIC
        # =====================================================================
        self.notification_topic = sns.Topic(
            self,
            "NotificationTopic",
            topic_name=f"{environment_name}-notifications",
        )

        if notification_email:
            self.notification_topic.add_subscription(
                subs.EmailSubscription(notification_email)
            )

        # =====================================================================
        # CLOUDWATCH LOG GROUP
        # =====================================================================
        self.log_group = logs.LogGroup(
            self,
            "StepFunctionsLogGroup",
            log_group_name=f"/aws/stepfunctions/{environment_name}",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # =====================================================================
        # IAM ROLES
        # =====================================================================

        # Lambda Execution Role
        self.lambda_role = iam.Role(
            self,
            "LambdaRole",
            role_name=f"{environment_name}-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Bedrock permissions
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:CreateModelInvocationJob",
                    "bedrock:GetModelInvocationJob",
                    "bedrock:ListModelInvocationJobs",
                ],
                resources=["*"],
            )
        )

        # S3 permissions
        self.bucket.grant_read_write(self.lambda_role)

        # CloudWatch permissions
        self.lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudwatch:PutMetricData"],
                resources=["*"],
            )
        )

        # SNS permissions
        self.notification_topic.grant_publish(self.lambda_role)

        # Step Functions Role
        self.sfn_role = iam.Role(
            self,
            "StepFunctionsRole",
            role_name=f"{environment_name}-sfn-role",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        )

        self.sfn_role.add_to_policy(
            iam.PolicyStatement(
                actions=["lambda:InvokeFunction"],
                resources=[f"arn:aws:lambda:{self.region}:{self.account}:function:{environment_name}-*"],
            )
        )

        self.sfn_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:CreateModelInvocationJob",
                    "bedrock:GetModelInvocationJob",
                ],
                resources=["*"],
            )
        )

        self.bucket.grant_read_write(self.sfn_role)
        self.notification_topic.grant_publish(self.sfn_role)

        self.sfn_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogDelivery",
                    "logs:GetLogDelivery",
                    "logs:UpdateLogDelivery",
                    "logs:DeleteLogDelivery",
                    "logs:ListLogDeliveries",
                    "logs:PutLogEvents",
                    "logs:PutResourcePolicy",
                    "logs:DescribeResourcePolicies",
                    "logs:DescribeLogGroups",
                ],
                resources=["*"],
            )
        )

        # Bedrock Batch Role
        self.bedrock_role = iam.Role(
            self,
            "BedrockBatchRole",
            role_name=f"{environment_name}-bedrock-role",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )
        self.bucket.grant_read_write(self.bedrock_role)

        # =====================================================================
        # LAMBDA FUNCTIONS
        # =====================================================================

        # Generate Red Team Prompts
        self.generate_red_fn = lambda_.Function(
            self,
            "GenerateRedPrompts",
            function_name=f"{environment_name}-generate-red-prompts",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="generate_red_prompts.handler",
            code=lambda_.Code.from_asset(str(lambda_dir / "batch")),
            role=self.lambda_role,
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "LOG_LEVEL": "INFO",
                "BUCKET_NAME": self.bucket.bucket_name,
            },
        )

        # Process Red Outputs
        self.process_red_fn = lambda_.Function(
            self,
            "ProcessRedOutputs",
            function_name=f"{environment_name}-process-red-outputs",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="process_red_outputs.handler",
            code=lambda_.Code.from_asset(str(lambda_dir / "batch")),
            role=self.lambda_role,
            timeout=Duration.minutes(10),
            memory_size=1024,
            environment={
                "LOG_LEVEL": "INFO",
                "BUCKET_NAME": self.bucket.bucket_name,
            },
        )

        # Run Judge
        self.run_judge_fn = lambda_.Function(
            self,
            "RunJudge",
            function_name=f"{environment_name}-run-judge",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="run_judge.handler",
            code=lambda_.Code.from_asset(str(lambda_dir / "batch")),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=2048,
            environment={
                "LOG_LEVEL": "INFO",
                "BUCKET_NAME": self.bucket.bucket_name,
                "NOTIFICATION_TOPIC_ARN": self.notification_topic.topic_arn,
            },
        )

        # Run Game (realtime)
        self.run_game_fn = lambda_.Function(
            self,
            "RunGame",
            function_name=f"{environment_name}-run-game",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="run_game.handler",
            code=lambda_.Code.from_asset(str(lambda_dir / "realtime")),
            role=self.lambda_role,
            timeout=Duration.minutes(15),
            memory_size=3008,
            environment={
                "LOG_LEVEL": "INFO",
                "BUCKET_NAME": self.bucket.bucket_name,
            },
        )

        # =====================================================================
        # STEP FUNCTIONS - Simple Sequential Workflow
        # =====================================================================

        # Simple workflow: Run games sequentially via Map state
        run_game_task = tasks.LambdaInvoke(
            self,
            "RunGameTask",
            lambda_function=self.run_game_fn,
            payload=sfn.TaskInput.from_json_path_at("$"),
            result_selector={
                "game_id.$": "$.Payload.game_id",
                "status.$": "$.Payload.status",
                "scoring.$": "$.Payload.scoring",
            },
        )

        # Add retry logic
        run_game_task.add_retry(
            errors=["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
            interval=Duration.seconds(30),
            max_attempts=3,
            backoff_rate=2,
        )
        run_game_task.add_retry(
            errors=["ThrottlingException"],
            interval=Duration.seconds(60),
            max_attempts=5,
            backoff_rate=2,
        )

        # Map state for running multiple games
        run_games_map = sfn.Map(
            self,
            "RunGamesMap",
            items_path="$.games",
            max_concurrency=1,  # Sequential to avoid throttling
            result_path="$.game_results",
        )
        run_games_map.item_processor(run_game_task)

        # Send completion notification
        send_notification = tasks.SnsPublish(
            self,
            "SendNotification",
            topic=self.notification_topic,
            message=sfn.TaskInput.from_text("Experiment complete! Check results in S3."),
            subject="Adversarial IaC Experiment Complete",
        )

        # Chain the workflow
        workflow_definition = run_games_map.next(send_notification)

        # Create state machine
        self.experiment_workflow = sfn.StateMachine(
            self,
            "ExperimentWorkflow",
            state_machine_name=f"{environment_name}-experiment",
            definition_body=sfn.DefinitionBody.from_chainable(workflow_definition),
            role=self.sfn_role,
            logs=sfn.LogOptions(
                destination=self.log_group,
                level=sfn.LogLevel.ALL,
            ),
        )

        # =====================================================================
        # CLOUDWATCH DASHBOARD
        # =====================================================================
        namespace = "AdversarialIaC/Experiments"

        self.dashboard = cloudwatch.Dashboard(
            self,
            "Dashboard",
            dashboard_name=f"{environment_name}-experiments",
        )

        self.dashboard.add_widgets(
            cloudwatch.TextWidget(
                markdown="# 🔬 Adversarial IaC Experiments",
                width=24,
                height=1,
            )
        )

        self.dashboard.add_widgets(
            cloudwatch.SingleValueWidget(
                title="Games Completed",
                metrics=[
                    cloudwatch.Metric(
                        namespace=namespace,
                        metric_name="GameCompleted",
                        statistic="Sum",
                        period=Duration.hours(24),
                    )
                ],
                width=6,
                height=4,
            ),
            cloudwatch.GaugeWidget(
                title="Avg Precision",
                metrics=[
                    cloudwatch.Metric(
                        namespace=namespace,
                        metric_name="Precision",
                        statistic="Average",
                        period=Duration.hours(1),
                    )
                ],
                left_y_axis=cloudwatch.YAxisProps(min=0, max=100),
                width=6,
                height=4,
            ),
            cloudwatch.GaugeWidget(
                title="Avg Evasion Rate",
                metrics=[
                    cloudwatch.Metric(
                        namespace=namespace,
                        metric_name="EvasionRate",
                        statistic="Average",
                        period=Duration.hours(1),
                    )
                ],
                left_y_axis=cloudwatch.YAxisProps(min=0, max=100),
                width=6,
                height=4,
            ),
        )

        # =====================================================================
        # OUTPUTS
        # =====================================================================
        CfnOutput(self, "BucketName", value=self.bucket.bucket_name)
        CfnOutput(self, "BucketArn", value=self.bucket.bucket_arn)
        CfnOutput(self, "LambdaRoleArn", value=self.lambda_role.role_arn)
        CfnOutput(self, "StepFunctionsRoleArn", value=self.sfn_role.role_arn)
        CfnOutput(self, "BedrockRoleArn", value=self.bedrock_role.role_arn)
        CfnOutput(self, "NotificationTopicArn", value=self.notification_topic.topic_arn)
        CfnOutput(self, "ExperimentWorkflowArn", value=self.experiment_workflow.state_machine_arn)
        CfnOutput(
            self,
            "DashboardURL",
            value=f"https://{self.region}.console.aws.amazon.com/cloudwatch/home?region={self.region}#dashboards:name={environment_name}-experiments",
        )
