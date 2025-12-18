import { Flex, Text, Theme } from '@radix-ui/themes';
import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';

type CommandItem = {
  id: string;
  label: string;
  description: string;
};

type CommandMentionListProps = {
  items: CommandItem[];
  command: (item: CommandItem) => void;
  editor: any;
};

const CommandMentionList = forwardRef(({ items, command }: CommandMentionListProps, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectItem = (index: number) => {
    const item = items[index];
    if (item) {
      command(item);
    }
  };

  const upHandler = () => {
    setSelectedIndex((selectedIndex + items.length - 1) % items.length);
  };

  const downHandler = () => {
    setSelectedIndex((selectedIndex + 1) % items.length);
  };

  const enterHandler = () => {
    selectItem(selectedIndex);
  };

  useEffect(() => {
    setSelectedIndex(0);
  }, [items]);

  useEffect(() => {
    const el = containerRef.current?.children[selectedIndex];
    if (el) {
      el.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  useImperativeHandle(ref, () => ({
    onKeyDown: ({ event }: { event: KeyboardEvent }) => {
      if (event.key === 'ArrowUp') {
        upHandler();
        return true;
      }
      if (event.key === 'ArrowDown') {
        downHandler();
        return true;
      }
      if (event.key === 'Enter') {
        enterHandler();
        return true;
      }
      return false;
    },
  }));

  return (
    <Theme accentColor="iris" panelBackground="translucent">
      <Flex
        direction="column"
        gap='0'
        className="shadow-lg dark:bg-panel-solid bg-white overflow-y-scroll max-h-96 rounded-md"
        ref={containerRef}
      >
        {items.length ? (
          items.map((item, index) => (
            <Flex
              key={item.id}
              role="button"
              align="center"
              title={item.label}
              aria-label={`Command ${item.label}`}
              className={`px-3 py-2 rounded-md cursor-pointer ${
                index === selectedIndex ? 'bg-accent-a5' : 'bg-panel-translucent'
              }`}
              onClick={() => selectItem(index)}
            >
              <Text as="span" weight="medium" size="2" style={{ marginRight: '8px' }}>
                {item.label}
              </Text>
              <Text as="span" color="gray" size="2">
                {item.description}
              </Text>
            </Flex>
          ))
        ) : (
          <div className="item px-3 py-2">No results</div>
        )}
      </Flex>
    </Theme>
  );
});

export default CommandMentionList;
