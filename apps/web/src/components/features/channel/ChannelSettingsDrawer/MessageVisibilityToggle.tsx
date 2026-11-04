import { useFrappeUpdateDoc } from 'frappe-react-sdk'
import { toast } from 'sonner'
import { Switch } from '@components/ui/switch'
import { PrefRow } from '@components/features/profile/PrefRows'
import { channelStore } from '@stores/channels/store'
import type { ChannelListItem } from '@raven/types/common/ChannelListItem'
import _ from '@lib/translate'

export function MessageVisibilityToggle({ channel }: { channel: ChannelListItem }) {
    const { updateDoc, loading } = useFrappeUpdateDoc()
    if (channel.type !== 'Private' || channel.is_direct_message) return null
    const update = async (checked: boolean) => {
        try {
            await updateDoc('Raven Channel', channel.name, { members_can_only_view_own_messages: checked ? 1 : 0 })
            // Reload clears already loaded messages when the visibility rule changes.
            channelStore.upsertChannel({ ...channel, members_can_only_view_own_messages: checked ? 1 : 0 })
            window.location.reload()
        } catch {
            toast.error(_('Could not change message visibility'))
        }
    }
    return <PrefRow label={_('Members only see their own messages')}
        description={_('Channel admins see all messages. Mentioned members can also see messages addressed to them.')}
        control={<Switch checked={!!channel.members_can_only_view_own_messages} disabled={loading} onCheckedChange={update} />} />
}
