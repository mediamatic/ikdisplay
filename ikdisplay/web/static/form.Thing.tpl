<form dojoType="dijit.form.Form">
    <div>
        Title:
        <input name="title" dojoType="dijit.form.TextBox" value="{title}" />
    </div>
    <div>
        URI:
        <input name="uri" dojoType="dijit.form.TextBox" value="{uri}" />
    </div>

    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.updateItem({_id}, this);">Save</button>
</form>

