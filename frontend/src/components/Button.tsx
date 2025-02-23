import {
  forwardRef,
  FunctionComponent,
  DetailedHTMLProps,
  ButtonHTMLAttributes,
} from "react"

type Props = {
  children: React.ReactNode
  variant?: "primary" | "secondary" | "destructive"
} & DetailedHTMLProps<
  ButtonHTMLAttributes<HTMLButtonElement>,
  HTMLButtonElement
>

const Button: FunctionComponent<Props> = forwardRef<HTMLButtonElement, Props>(
  ({ children, variant = "primary", className, ...buttonProps }, ref) => {
    const variantClass = {
      destructive:
        "bg-bgColorSecondary text-colorDanger border border-colorDanger disabled:borden-none disabled:text-gray-100 enabled:hover:bg-colorDanger enabled:hover:text-gray-100",
      secondary:
        "bg-bgColorSecondary text-textSecondary border border-textSecondary disabled:border-none disabled:text-gray-100 disabled:bg-gray-500 enabled:hover:opacity-50",
      primary:
        "bg-colorPrimary text-gray-100 disabled:bg-gray-400 enabled:hover:opacity-75",
    }[variant]

    return (
      <button
        className={`${
          className ?? ""
        } ${variantClass} no-wrap h-11 overflow-hidden text-ellipsis whitespace-nowrap px-5 py-2 text-center duration-500 active:bg-bgColorPrimary active:text-colorPrimary enabled:hover:cursor-pointer disabled:cursor-default`}
        type={buttonProps.type}
        ref={ref}
        {...buttonProps}
      >
        {children}
      </button>
    )
  },
)

Button.displayName = "Button"

export default Button
