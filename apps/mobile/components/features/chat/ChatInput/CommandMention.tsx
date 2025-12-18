import React, { FC, useMemo } from 'react';
import { View, Pressable, Text } from 'react-native';
import useFetchChannelCommands from '@hooks/useFetchChannelCommands';

type Command = {
  id: string;
  name: string;
  description?: string;
  script: string;
  botName: string;
};

type Props = {
  keyword: string | null;
  onSuggestionPress: (command: Command) => void;
  channelID: string;
};

export const CommandMentions: FC<Props> = ({ keyword, onSuggestionPress, channelID }) => {
  const { channelCommands } = useFetchChannelCommands(channelID);

  const allCommands: Command[] = useMemo(() => {
    const result: Command[] = [];

    for (const botName in channelCommands) {
      const botCommands = channelCommands[botName];

      botCommands.forEach((cmd, index) => {
        result.push({
          id: `${botName}_${cmd.command_name}_${index}`,
          name: cmd.command_name,
          description: cmd.command_description,
          script: cmd.command_script,
          botName
        });
      });
    }

    return result;
  }, [channelCommands]);

  const filteredCommands = useMemo(() => {
    if (!keyword) return allCommands.slice(0, 5);

    const k = keyword.toLowerCase();

    return allCommands
      .filter((cmd) => cmd.name.toLowerCase().includes(k))
      .slice(0, 5);
  }, [allCommands, keyword]);

  if (keyword == null || filteredCommands.length === 0) return null;

  return (
    <View className="flex flex-col border-b border-border rounded-md bg-background">
      {filteredCommands.map((cmd) => (
        <Pressable
          key={cmd.id}
          hitSlop={10}
          className="active:bg-card-background/50 py-1.5 px-2"
          onPress={() => onSuggestionPress(cmd)}
        >
          <View className="flex flex-row items-center gap-2">
            <Text className="text-sm"></Text>
            <View className="flex flex-col">
              <Text className="text-sm text-foreground font-medium">/{cmd.name}</Text>
              {cmd.description && (
                <Text className="text-xs text-muted-foreground">{cmd.description}</Text>
              )}
              <Text className="text-[10px] text-muted-foreground italic">from: {cmd.botName}</Text>
            </View>
          </View>
        </Pressable>
      ))}
    </View>
  );
};
