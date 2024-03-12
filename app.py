import os
import io
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
import google.generativeai as genai
from langchain_community.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

# Set the API key
GOOGLE_API_KEY = "AIzaSyCSfZn0ghAgQSv9LRN6Bf2HX_iiugV32ok"
genai.configure(api_key=GOOGLE_API_KEY)

def get_pdf_text(pdf_bytes):
    """Extracts text from uploaded PDFs."""
    text = ""
    pdf_stream = io.BytesIO(pdf_bytes)
    pdf_reader = PdfReader(pdf_stream)
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text


def get_text_chunks(text):
    """Splits text into chunks for vectorization."""
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks


def get_vector_store(text_chunks):
    """Creates or loads the FAISS vector store."""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001",google_api_key=GOOGLE_API_KEY)
    vector_store = FAISS.from_texts(text_chunks,embedding=embeddings)
    vector_store.save_local("faiss_index")
    return vector_store


def get_conversational_chain():
    """Creates the question-answering chain."""
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide context,
    make sure to provide all the details, if the answer is not in provided context just say, "answer is not in the context",
    don't provide the wrong answer\n\n
    Context:\n {context}?\n
    Question:\n {question}\n
    
    Answer:
    """
    model = ChatGoogleGenerativeAI(model='gemini-pro', temperature=0.3, google_api_key=GOOGLE_API_KEY)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", 'question'])
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain


def user_input(user_question):
    """Processes user question and retrieves answer from PDFs."""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001",google_api_key=GOOGLE_API_KEY)
    
    new_db = FAISS.load_local("faiss_index",embeddings=embeddings,allow_dangerous_deserialization=True)
    docs = new_db.similarity_search(user_question)

    chain = get_conversational_chain()
    response = chain(
        {"input_documents": docs, "question": user_question}
        , return_only_outputs=True)
    print(response)
    st.write("Reply: ",response["output_text"])

   
def main():
    st.set_page_config("Chat with Multiple PDF")
    st.header("Chat with your PDF's using Gemini")

    # Empty placeholder for user response
    user_response = st.empty()

    # Sidebar for PDF upload and processing
    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader("Upload your PDF docs and click Submit")

        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs.getvalue())
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                st.success("Done")


    # Text input for user question
    user_question = st.text_input("Ask a Question from the PDF Files")

    # Update user response based on user input
    if user_question:
        user_input(user_question)


if __name__ == "__main__":
    main()
