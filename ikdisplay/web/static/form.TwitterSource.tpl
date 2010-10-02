<form dojoType="dijit.form.Form">
    <div>
        Terms:
        <textarea name="terms" dojoType="dijit.form.Textarea">{.repeated section terms}{@}
{.end}</textarea>
    </div>

    <div>
        User IDs:
        <textarea name="userIDs" dojoType="dijit.form.Textarea">{.repeated section userIDs}{@}
{.end}</textarea>
    </div>

    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.updateItem({_id}, this);">Save</button>
</form>

