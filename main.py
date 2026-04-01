import os
import io
import zipfile
import streamlit as st
from PIL import Image, PngImagePlugin
import piexif
from piexif import helper

st.set_page_config(page_title="SEO Image EXIF Optimizer", page_icon="🖼️", layout="wide")
st.title("🖼️ SEO Image EXIF Optimizer")
st.caption("Upload images, inject SEO keywords, and download optimised files.")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
PNG_TEXT_LIMIT = 7900

def decode_bytes(value):
    if isinstance(value, bytes):
        for enc in ("utf-8", "utf-16le", "latin-1"):
            try:
                return value.decode(enc).rstrip("\x00")
            except UnicodeDecodeError:
                continue
        return value.decode("utf-8", errors="replace").rstrip("\x00")
    return value

def empty_exif():
    return {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}

def extract_metadata(data, filename):
    ext = os.path.splitext(filename)[1].lower()
    image = Image.open(io.BytesIO(data))
    meta = {"File": filename, "Format": image.format or "Unknown",
            "Size": f"{image.width} x {image.height}",
            "Keywords": "Not available", "User comment": "Not available"}
    if ext in (".jpg", ".jpeg"):
        exif_bytes = image.info.get("exif", b"")
        exif_dict = piexif.load(exif_bytes) if exif_bytes else empty_exif()
        xp = exif_dict["0th"].get(piexif.ImageIFD.XPKeywords)
        if xp:
            meta["Keywords"] = decode_bytes(xp) or "Not available"
        uc = exif_dict["Exif"].get(piexif.ExifIFD.UserComment)
        if uc:
            try:
                meta["User comment"] = helper.UserComment.load(uc)
            except Exception:
                meta["User comment"] = decode_bytes(uc) or "Not available"
    else:
        meta["Keywords"] = image.info.get("Keywords", "Not available")
        meta["User comment"] = image.info.get("UserComment", "Not available")
    image.close()
    return meta

def inject_keywords(data, filename, keywords):
    ext = os.path.splitext(filename)[1].lower()
    keyword_text = ", ".join(keywords)
    image = Image.open(io.BytesIO(data))
    buf = io.BytesIO()
    if ext in (".jpg", ".jpeg"):
        exif_bytes = image.info.get("exif", b"")
        exif_dict = piexif.load(exif_bytes) if exif_bytes else empty_exif()
        exif_dict["0th"][piexif.ImageIFD.ImageDescription] = keyword_text.encode("utf-8")
        exif_dict["0th"][piexif.ImageIFD.XPKeywords] = keyword_text.encode("utf-16le") + b"\x00\x00"
        exif_dict["Exif"][piexif.ExifIFD.UserComment] = helper.UserComment.dump(keyword_text, encoding="unicode")
        image.save(buf, format="JPEG", exif=piexif.dump(exif_dict), quality=95)
    else:
        png_info = PngImagePlugin.PngInfo()
        for k, v in image.info.items():
            if isinstance(v, str):
                png_info.add_text(k, v[:PNG_TEXT_LIMIT])
        png_info.add_text("Keywords", keyword_text[:PNG_TEXT_LIMIT])
        png_info.add_text("Description", keyword_text[:PNG_TEXT_LIMIT])
        image.save(buf, format="PNG", pnginfo=png_info)
    image.close()
    return buf.getvalue()

def slugify(value):
    cleaned = []
    for ch in value.strip().lower():
        if ch.isalnum():
            cleaned.append(ch)
        elif ch in {" ", "-", "_"}:
            cleaned.append("-")
    slug = "".join(cleaned)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")

# ── Sidebar ──
with st.sidebar:
    st.header("⚙️ Settings")
    keywords_raw = st.text_area("Keywords (one per line)", value="handmade jewelry\nsterling silver ring\nboho style", height=200)
    keywords = [k.strip() for k in keywords_raw.splitlines() if k.strip()]
    st.caption(f"{len(keywords)} keyword(s)")
    main_keyword = st.text_input("Main keyword for renaming", value=keywords[0] if keywords else "")
    do_rename = st.checkbox("Rename files", value=False)

# ── Upload ──
uploaded_files = st.file_uploader("Upload images (JPG / PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if not uploaded_files:
    st.info("👆 Upload images to get started")
    st.stop()

st.subheader(f"📋 {len(uploaded_files)} image(s) uploaded")
for uf in uploaded_files:
    data = uf.read(); uf.seek(0)
    with st.expander(f"🔍 {uf.name}"):
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(data, use_container_width=True)
        with col2:
            for k, v in extract_metadata(data, uf.name).items():
                st.markdown(f"**{k}:** {v}")

st.divider()

if st.button("💉 Inject Keywords & Download ZIP", type="primary", use_container_width=True):
    if not keywords:
        st.warning("Add keywords in the sidebar first!")
        st.stop()
    zip_buf = io.BytesIO()
    results = []
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx, uf in enumerate(uploaded_files, start=1):
            data = uf.read()
            try:
                injected = inject_keywords(data, uf.name, keywords)
                slug = slugify(main_keyword) if main_keyword else slugify(uf.name)
                ext = os.path.splitext(uf.name)[1].lower()
                out_name = (f"{slug}{ext}" if idx == 1 else f"{slug}-{idx}{ext}") if do_rename else uf.name
                zf.writestr(out_name, injected)
                results.append(("✅", uf.name, out_name))
            except Exception as e:
                results.append(("❌", uf.name, str(e)))
    zip_buf.seek(0)
    st.download_button("⬇️ Download ZIP", data=zip_buf, file_name="seo-images.zip", mime="application/zip", use_container_width=True)
    for status, orig, out in results:
        st.markdown(f"{status} `{orig}` → `{out}`")