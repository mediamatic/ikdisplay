<form dojoType="dijit.form.Form">
    <div>
        Title:
        <input name="title" dojoType="dijit.form.TextBox" value="{title}" />
    </div>

    <div>
        Language:
        <input name="language" dojoType="dijit.form.TextBox" value="{language}" />
    </div>

    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.updateItem({_id}, this);">Save</button>
</form>

