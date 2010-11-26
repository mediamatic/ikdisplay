<form dojoType="dijit.form.Form">
    <div>
        Service:
        <input name="service" dojoType="dijit.form.TextBox" {.section service}value="{@}"{.end} />
    </div>
    <div>
        Node:
        <input name="nodeIdentifier" dojoType="dijit.form.TextBox" {.section nodeIdentifier}value="{@}"{.end} />
    </div>

    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.updateItem({_id}, this);">Save</button>
</form>
