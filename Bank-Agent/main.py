from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel, RunConfig, function_tool, input_guardrail
from dotenv import load_dotenv
from pydantic import BaseModel
import os


load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

external_client = AsyncOpenAI(
    api_key = gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

model = OpenAIChatCompletionsModel(
    model = "gemini-2.0-flash",
    openai_client = external_client
)

config = RunConfig(
    model = model,
    model_provider = external_client,
)

class Account(BaseModel):
   name : str
   pin : int

class Guardrail_output(BaseModel):
   is_bank_related : bool
   tripwire_triggered : bool


guardrail_agent = Agent(
    name = "Guardrail Agent",
    instructions = "You are a guardrail agent, your task is to ensure that all queries are related to banking.",
    output_type = Guardrail_output,
    model = model
)

@input_guardrail
async def check_bank_related(agent, input, context):
    text = input if isinstance(input, str) else str(input)

    if "balance" in text.lower() or "account" in text.lower() or "bank" in text.lower():
        return Guardrail_output(is_bank_related=True, tripwire_triggered=False)
    else:
        return Guardrail_output(is_bank_related=False, tripwire_triggered=True)


def check_user_related(ctx, tool):
    if ctx.context.name == "Muskan" and ctx.context.pin == 54321:
        return True
    return False

   
@function_tool(is_enabled = check_user_related)
def check_balance(account_number : str) -> str:
   return f"Balance for account {account_number} is $10000."


Bank_Agent = Agent(
    name = "Bank Agent",
    instructions = "You are a bank agent, your task is to assist customers with their banking queries.",
    tools = [check_balance],
    input_guardrails = [check_bank_related]
)

Balance_Agent = Agent(
    name = "Balance Agent",
    instructions = "You are a balance agent, your task is to provide account balance information.",
    tools = [check_balance],
    input_guardrails = [check_bank_related]
)

triage_agent = Agent(
   name = "Triage Agent",
   instructions = "You are a triage agent, your task is to route queries to the appropriate agent.",
   tools = [Bank_Agent, Balance_Agent],
   input_guardrails = [check_bank_related]
)

user_context = Account(name="Muskan", pin=54321)

result = Runner.run_sync(
    Bank_Agent,
    input="My account number is 12345, What is my account balance?",
    context=user_context,
    run_config=config
)
