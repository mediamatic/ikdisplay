<h1>{title}</h1>

<table border="1">
    <tr>
        <th>&nbsp;</th>
        <th>Title</th>
        <th>Type</th>
        <th>&nbsp;</th>
    </tr>
    {.repeated section sources}
    <tr class="{.section enabled}enabled{.or}disabled{.end}">
        <td><input type="checkbox" name="enabled" {.section enabled}checked="checked"{.end} onclick="BackChannel.actions.toggleEnabled({_id}, {.section enabled}true{.or}false{.end})" /></td>
        <td>{_title}</td>
        <td>{_type}</td>
        <td>
            <a href="javascript:;" onclick="BackChannel.actions.editItem({_id}, 'Edit {_type}', '{_class}')">edit</a>
            <a href="javascript:;" onclick="BackChannel.actions.removeItem({_id})">remove</a>
        </td>
    </tr>
    {.end}
</table>


<p>Add new
    <select onchange="BackChannel.actions.addSource({_id}, this.value)">
        <option value="">choose source...</option>
        {.repeated section allSources}
        <option value="{0}">{1}</option>
        {.end}
    </select>
</p>
<p>
    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.editItem({_id}, 'Edit feed', 'Feed')">Edit feed</button>
</p>

