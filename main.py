from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import PyPDF2
from PIL import Image
import os

BOT_TOKEN = "7686870648:AAHQNNc48057w-hvZq0hDvtzgyYAZjOja0I"

# Store uploaded PDFs for merging
user_files = {}
# Store last uploaded PDF for each user
last_pdf = {}

# Handle multiple PDF uploads for merging
async def handle_merge_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    file = await update.message.document.get_file()
    file_path = f"{user_id}_{update.message.document.file_name}"
    await file.download_to_drive(file_path)
    user_files.setdefault(user_id, []).append(file_path)
    await update.message.reply_text(
        "PDF added for merging. Send more PDFs or use /domerge to combine them."
    )

# Save last uploaded PDF for /doimage
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    file = await update.message.document.get_file()
    file_path = f"{user_id}.pdf"
    await file.download_to_drive(file_path)
    last_pdf[user_id] = file_path
    await update.message.reply_text(
        "PDF received. Use /doimage to convert its pages to images."
    )

# Merge PDFs command
async def merge_pdfs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    files = user_files.get(user_id, [])
    if len(files) < 2:
        await update.message.reply_text("Please upload at least two PDFs to merge.")
        return
    merger = PyPDF2.PdfMerger()
    for file in files:
        merger.append(file)
    output = f"{user_id}_merged.pdf"
    with open(output, "wb") as f_out:
        merger.write(f_out)
    await update.message.reply_document(document=open(output, "rb"))
    # Clean up
    for file in files:
        os.remove(file)
    os.remove(output)
    user_files[user_id] = []

# Convert PDF to images
async def pdf_to_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    file_path = last_pdf.get(user_id)
    if not file_path or not os.path.exists(file_path):
        await update.message.reply_text("Please send a PDF first.")
        return
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            writer = PyPDF2.PdfWriter()
            writer.add_page(page)
            temp_pdf = f"temp_{i+1}.pdf"
            with open(temp_pdf, "wb") as temp_f:
                writer.write(temp_f)
            await update.message.reply_document(document=open(temp_pdf, "rb"))
            os.remove(temp_pdf)
    os.remove(file_path)
    last_pdf[user_id] = None

# Convert JPG images to PDF
async def jpg_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Please send a JPG image.")
        return
    photo = update.message.photo[-1]
    file = await photo.get_file()
    file_path = f"{update.message.from_user.id}_input.jpg"
    await file.download_to_drive(file_path)
    image = Image.open(file_path).convert("RGB")
    pdf_path = f"{update.message.from_user.id}_output.pdf"
    image.save(pdf_path, "PDF", resolution=100.0)
    await update.message.reply_document(document=open(pdf_path, "rb"))
    os.remove(file_path)
    os.remove(pdf_path)

# Add start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Available commands:\n"
        "/merge - Instructions for merging PDFs\n"
        "/domerge - Merge uploaded PDFs\n"
        "/toimage - Instructions for PDF to images\n"
        "/doimage - Convert your last uploaded PDF to images\n"
        "/jpg2pdf - Instructions for JPG to PDF\n"
        "Just send a PDF or image to get started!"
    )

# Prompt user to send PDF for merging
async def merge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send PDFs with caption 'merge' to add them for merging. When done, use /domerge to combine."
    )

# Prompt user to send PDF for image conversion
async def toimage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send a PDF file to convert its pages to images, then use /doimage."
    )

# Prompt user to send JPG for PDF conversion
async def jpg2pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send a JPG image to convert it to PDF."
    )

app = Application.builder().token(BOT_TOKEN).build()
# File handlers first
app.add_handler(MessageHandler(filters.Document.PDF & filters.Caption() & filters.Regex("merge"), handle_merge_pdf))
app.add_handler(MessageHandler(filters.Document.PDF & ~(filters.Caption() & filters.Regex("merge")), handle_pdf))
app.add_handler(MessageHandler(filters.PHOTO, jpg_to_pdf))
# Command handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("merge", merge_command))
app.add_handler(CommandHandler("domerge", merge_pdfs))
app.add_handler(CommandHandler("toimage", toimage_command))
app.add_handler(CommandHandler("doimage", pdf_to_images))
app.add_handler(CommandHandler("jpg2pdf", jpg2pdf_command))

print("Bot is running...")
app.run_polling()
