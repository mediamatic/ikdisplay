<form dojoType="dijit.form.Form">
    <div>
        Title:
        <input name="title" dojoType="dijit.form.ValidationTextBox" value="" required="true" />
    </div>

    <div>
        Language:
        <input name="language" dojoType="dijit.form.ValidationTextBox" value="en" required="true" />
    </div>

    <div>
        Handle:
        <input name="handle" dojoType="dijit.form.ValidationTextBox" value="" required="true" />
    </div>

    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.insertFeed(this);">Save</button>
</form>

