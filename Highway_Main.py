import marimo

__generated_with = "0.13.13"
app = marimo.App(width="columns")


@app.cell
def _():
    import marimo as mo
    import nasa_power
    import kml_process
    import io
    return io, kml_process, mo


@app.cell
def _(mo):
    file_upload_widget = mo.ui.file(kind="area")
    file_upload_widget
    return (file_upload_widget,)


@app.cell
def _(file_upload_widget, io, kml_process):
    file_content = file_upload_widget.value[0].contents
    file_object = io.BytesIO(file_content)
    kml_process.load_kml_file(file_object)
    return


if __name__ == "__main__":
    app.run()
