<h1>Things</h1>

<table class="list things">
    <tr>
        <th>Title</th>
        <th>URI</th>
        <th class="actions">&nbsp;</th>
    </tr>
    
    {.repeated section @}
    <tr>
        <td>{title}</td>
        <td>{uri}</td>
        <td>
            <a href="javascript:;" onclick="BackChannel.actions.editItem({_id}, 'Edit thing', 'Thing')">edit</a>
            <a href="javascript:;" onclick="BackChannel.actions.removeItem({_id})">remove</a>
        </td>
    </tr>
    {.end}
</table>

<p>
    <button dojoType="dijit.form.Button" onClick="BackChannel.actions.addThing();">Create new thing</button>
</p>
