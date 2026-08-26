# Actionable items, decisions, questions

import os
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda


def get_llm():
    return ChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0.2,
    )


def build_chain(system_prompt: str):
    llm = get_llm()
    return (
        RunnablePassthrough()
        | RunnableLambda(lambda x: {"text": x})
        | ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{text}"),
        ])
        | llm
        | StrOutputParser()
    )


def extract_action_items(transcript: str) -> str:
    chain = build_chain(
        "You are an expert AI assistant analyzing a video or meeting transcript.\n"
        "Extract all action items, next steps, or practical recommendations/takeaways.\n\n"
        "Instructions:\n"
        "- If it is a meeting, list tasks, owners, and deadlines (if mentioned).\n"
        "- If it is a presentation, speech, or general video, list 2-4 key practical takeaways or advice provided.\n"
        "- Format as a numbered list.\n"
        "- Do NOT say 'No action items found' unless the text is completely empty."
    )
    return chain.invoke(transcript)


def extract_key_decisions(transcript: str) -> str:
    chain = build_chain(
        "You are an expert AI assistant analyzing a video or meeting transcript.\n"
        "Extract all key decisions, core arguments, or main conclusions made.\n\n"
        "Instructions:\n"
        "- If it is a meeting, list formal decisions reached.\n"
        "- If it is a presentation, speech, or general video, summarize the top 2-3 main conclusions or central points.\n"
        "- Format as a numbered list.\n"
        "- Do NOT say 'No key decisions found' unless the text is completely empty."
    )
    return chain.invoke(transcript)


def extract_questions(transcript: str) -> str:
    chain = build_chain(
        "From the transcript, extract all unresolved questions, key questions addressed, "
        "or topics needing follow-up. Format as a numbered list."
    )
    return chain.invoke(transcript)