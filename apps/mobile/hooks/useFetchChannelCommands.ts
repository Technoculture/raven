import { useFrappeGetCall } from "frappe-react-sdk"

export type BotCommand = {
  command_name: string;
  command_description: string;
  command_script: string;
};

export type ChannelCommands = {
  [botName: string]: BotCommand[];
};


const useFetchChannelCommands = (channelID: string) => {

    const { data, error, isLoading, mutate } = useFrappeGetCall<{ message: ChannelCommands }>('raven.api.chat.get_channel_commands', {
        channel_id: channelID
    }, ["channel_commands", channelID], {
        keepPreviousData: true,
        dedupingInterval: 1000 * 60 * 5, 
    })

    return {
        channelCommands: data?.message ?? {},
        error,
        isLoading,
        mutate
    }
}

export default useFetchChannelCommands