# @Time    : 2026/3/2 14:42
# @Author  : Yun
# @FileName: interrupt_test
# @Software: PyCharm
# @Desc    :
import sqlite3
from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command, interrupt


class ReviewState(TypedDict):
    generated_text: str


def review_node(state: ReviewState):
    # Ask a reviewer to edit the generated content
    updated = interrupt({
        "instruction": "Review and edit this content",
        "content": state["generated_text"],
    })
    return {"generated_text": updated}


def mmmm(state: ReviewState):
    print("assd")
    return state


def arae(state: ReviewState):
    print("arae")
    return "mmmm"


builder = StateGraph(ReviewState)
builder.add_node("review", review_node)
builder.add_node("mmmm", mmmm)
builder.add_edge(START, "review")
builder.add_conditional_edges("review", arae, ["mmmm", END])
builder.add_edge("mmmm", END)

checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "review-42"}}
interrupted = False
first_input = input("Please enter your first input: ")
for chunk in graph.invoke({"generated_text": first_input}, config=config, stream_mode="updates"):
    if "__interrupt__" in chunk:
        print("检测到interrupt:", chunk["__interrupt__"])
        interrupted = True
        break  # 暂停，等待用户输入
# initial = graph.invoke({"generated_text": "Initial draft"}, config=config)
if not interrupted:
    final_state = graph.get_state(config=config)
else:
    interrupt = graph.get_state(config)
    print("interrupted:", interrupt)
    second_input = input("Please enter your second input: ")

    # print(initial["__interrupt__"])  # -> [Interrupt(value={'instruction': ..., 'content': ...})]

    # Resume with the edited text from the reviewer
    final_state = graph.invoke(
        Command(resume=second_input),
        config=config,
    )
print(final_state["generated_text"])  # -> "Improved draft after review"
